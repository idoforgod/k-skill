from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html import unescape
from typing import Any

IMPROPER_FOOD_ENDPOINT = "https://apis.data.go.kr/1471000/PrsecImproptFoodInfoService03/getPrsecImproptFoodList01"
FOOD_RECALL_SAMPLE_URL = "https://openapi.foodsafetykorea.go.kr/api/sample/I0490/json/{start}/{end}"
FOOD_RECALL_LIVE_URL = "https://openapi.foodsafetykorea.go.kr/api/{api_key}/I0490/json/{start}/{end}"


class ApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, url: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.url = url


def summarize_text(value: Any) -> str:
    if value is None:
        return ""
    text = unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def resolve_data_go_service_key(explicit_key: str | None, env: dict[str, str] | None = None) -> str:
    env = env or os.environ
    candidate = explicit_key or env.get("DATA_GO_KR_API_KEY")
    if not candidate:
        raise ValueError("DATA_GO_KR_API_KEY 또는 --service-key 가 필요합니다.")
    return urllib.parse.unquote(str(candidate).strip())


def build_food_interview(question: str | None = None, symptoms: str | None = None) -> dict[str, Any]:
    return {
        "domain": "food",
        "question": summarize_text(question),
        "symptoms": summarize_text(symptoms),
        "must_ask": [
            "누가 먹었거나 먹으려는지 알려주세요. (본인/아이/임산부/고령자)",
            "무엇을 언제 먹었는지, 얼마나 먹었는지 알려주세요.",
            "같이 먹은 음식이나 술, 복용 중인 약이 있는지 알려주세요.",
            "복통·구토·설사·발진 같은 증상이 언제부터 시작됐는지 알려주세요.",
            "기저질환, 임신 여부, 알레르기 여부를 알려주세요.",
        ],
        "red_flags": [
            "호흡곤란, 입술·혀 붓기 같은 급성 알레르기 반응",
            "혈변 또는 검은변",
            "심한 탈수, 소변 감소, 계속되는 구토",
            "의식저하, 고열, 심한 복통",
        ],
        "urgent_action": "red flag 가 있으면 식품 조회보다 즉시 응급실·119·의료진 연결을 우선하세요.",
        "policy": "이 helper 는 공식 식품 안전정보 조회 전에 반드시 되묻기 흐름을 제공하며, 먹어도 되는지 단정하지 않습니다.",
    }


def normalize_food_recall_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "foodsafetykorea_recall",
        "product_name": summarize_text(row.get("PRDLST_NM") or row.get("PRDTNM")),
        "company_name": summarize_text(row.get("BSSH_NM") or row.get("BSSHNM")),
        "reason": summarize_text(row.get("RTRVLPRVNS")),
        "created_at": summarize_text(row.get("CRET_DTM")),
        "distribution_deadline": summarize_text(row.get("DISTBTMLMT")),
        "category": summarize_text(row.get("PRDLST_TYPE") or row.get("PRDLST_CD_NM")),
    }


def normalize_improper_food_item(item: dict[str, Any]) -> dict[str, Any]:
    reason_parts = [summarize_text(item.get("IMPROPT_ITM")), summarize_text(item.get("INSPCT_RESULT"))]
    return {
        "source": "mfds_improper_food",
        "product_name": summarize_text(item.get("PRDUCT")),
        "company_name": summarize_text(item.get("ENTRPS")),
        "reason": "; ".join(part for part in reason_parts if part),
        "created_at": summarize_text(item.get("REGIST_DT")),
        "category": summarize_text(item.get("FOOD_TY")),
    }


def filter_food_items(items: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    needle = summarize_text(query).casefold()
    if not needle:
        return items

    product_matches = [
        item for item in items if needle in summarize_text(item.get("product_name")).casefold()
    ]
    if product_matches:
        return product_matches

    company_matches = [
        item for item in items if needle in summarize_text(item.get("company_name")).casefold()
    ]
    if company_matches:
        return company_matches

    return [
        item for item in items if needle in summarize_text(item.get("reason")).casefold()
    ]


def _request_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    full_url = url
    if params:
        full_url = f"{url}?{urllib.parse.urlencode({key: value for key, value in params.items() if value not in (None, '')})}"
    request = urllib.request.Request(full_url, headers={"Accept": "application/json", "User-Agent": "k-skill-mfds/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            try:
                return json.loads(body)
            except json.JSONDecodeError as error:
                hostname = (urllib.parse.urlparse(request.full_url).hostname or "").casefold()
                if hostname == "openapi.foodsafetykorea.go.kr":
                    raise ApiError(
                        "식품안전나라 응답이 JSON이 아닙니다. --foodsafetykorea-key 가 유효한지 확인하세요.",
                        url=request.full_url,
                    ) from error

                content_type = summarize_text(response.headers.get("Content-Type") or "unknown")
                raise ApiError(
                    f"MFDS food response was not valid JSON (content-type: {content_type})",
                    url=request.full_url,
                ) from error
    except urllib.error.HTTPError as error:
        raise ApiError(f"MFDS food request failed with HTTP {error.code}", status_code=error.code, url=request.full_url) from error


def _extract_improper_food_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    body = payload.get("body") or {}
    items = body.get("items") or {}
    raw = items.get("item")
    if raw is None:
        return []
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        return [raw]
    return []


def _extract_food_recall_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    root = payload.get("I0490") or {}
    rows = root.get("row")
    if rows is None:
        return []
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    if isinstance(rows, dict):
        return [rows]
    return []


def fetch_improper_food_items(service_key: str, *, limit: int = 100, request_json: Any = _request_json) -> list[dict[str, Any]]:
    payload = request_json(
        IMPROPER_FOOD_ENDPOINT,
        {"ServiceKey": service_key, "pageNo": 1, "numOfRows": limit, "type": "json"},
    )
    return [normalize_improper_food_item(item) for item in _extract_improper_food_items(payload)]


def fetch_food_recall_rows(
    *,
    limit: int = 100,
    sample: bool = False,
    foodsafety_api_key: str | None = None,
    request_json: Any = _request_json,
) -> list[dict[str, Any]]:
    start = 1
    end = max(limit, 1)
    if sample or not foodsafety_api_key:
        url = FOOD_RECALL_SAMPLE_URL.format(start=start, end=end)
    else:
        url = FOOD_RECALL_LIVE_URL.format(api_key=foodsafety_api_key, start=start, end=end)
    payload = request_json(url)
    return [normalize_food_recall_row(row) for row in _extract_food_recall_rows(payload)]


def search_food_safety(
    query: str,
    *,
    service_key: str | None = None,
    foodsafety_api_key: str | None = None,
    sample_recalls: bool = False,
    limit: int = 10,
    request_json: Any = _request_json,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    warnings: list[str] = []

    if service_key:
        try:
            items.extend(fetch_improper_food_items(service_key, limit=max(limit * 5, 50), request_json=request_json))
        except ApiError as error:
            warnings.append(str(error))
    else:
        warnings.append("DATA_GO_KR_API_KEY 가 없어 부적합 식품 live 조회는 건너뜁니다.")

    if sample_recalls or foodsafety_api_key:
        try:
            items.extend(
                fetch_food_recall_rows(
                    limit=max(limit * 5, 50),
                    sample=sample_recalls,
                    foodsafety_api_key=foodsafety_api_key,
                    request_json=request_json,
                )
            )
        except ApiError as error:
            warnings.append(str(error))
    else:
        warnings.append("식품안전나라 회수 정보는 --sample-recalls 또는 --foodsafetykorea-key 가 필요합니다.")

    filtered = filter_food_items(items, query)[:limit]
    return {
        "query": query,
        "items": filtered,
        "warnings": warnings,
        "note": "이 결과는 공식 회수·부적합 공개 목록 기반 참고 정보이며, 먹어도 되는지의 최종 판단은 증상 인터뷰와 의료진 상담이 우선입니다.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MFDS food-safety helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    interview = subparsers.add_parser("interview", help="print the mandatory symptom follow-up interview")
    interview.add_argument("--question", default="")
    interview.add_argument("--symptoms", default="")

    search = subparsers.add_parser("search", help="search official food recall/improper food records")
    search.add_argument("--query", required=True)
    search.add_argument("--service-key")
    search.add_argument("--foodsafetykorea-key")
    search.add_argument("--sample-recalls", action="store_true")
    search.add_argument("--limit", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "interview":
        print(json.dumps(build_food_interview(question=args.question, symptoms=args.symptoms), ensure_ascii=False, indent=2))
        return 0

    if args.command == "search":
        try:
            service_key = None
            if args.service_key or os.environ.get("DATA_GO_KR_API_KEY"):
                service_key = resolve_data_go_service_key(args.service_key)
            payload = search_food_safety(
                args.query,
                service_key=service_key,
                foodsafety_api_key=args.foodsafetykorea_key,
                sample_recalls=args.sample_recalls,
                limit=args.limit,
            )
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        except ValueError as error:
            print(json.dumps({"error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
