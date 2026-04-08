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

DRUG_EASY_ENDPOINT = "https://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList"
SAFE_STAD_ENDPOINT = "https://apis.data.go.kr/1471000/SafeStadDrugService/getSafeStadDrugInq"


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


def resolve_service_key(explicit_key: str | None, env: dict[str, str] | None = None) -> str:
    env = env or os.environ
    candidate = explicit_key or env.get("DATA_GO_KR_API_KEY")
    if not candidate:
        raise ValueError("DATA_GO_KR_API_KEY 또는 --service-key 가 필요합니다.")
    return urllib.parse.unquote(str(candidate).strip())


def build_drug_interview(question: str | None = None, symptoms: str | None = None) -> dict[str, Any]:
    return {
        "domain": "drug",
        "question": summarize_text(question),
        "symptoms": summarize_text(symptoms),
        "must_ask": [
            "누가 복용하려는지 알려주세요. (본인/아이/임산부/고령자)",
            "무슨 약을 이미 먹었거나 지금 먹으려는지, 제품명/성분명을 각각 알려주세요.",
            "언제부터, 얼마나 자주, 한 번에 얼마나 복용했는지 알려주세요.",
            "지금 있는 증상과 언제 시작됐는지 알려주세요.",
            "복용 중인 약, 기저질환, 알레르기 여부를 알려주세요.",
        ],
        "red_flags": [
            "호흡곤란 또는 숨쉬기 힘듦",
            "의식저하, 실신, 혼동",
            "입술·혀 붓기 또는 심한 전신 발진",
            "지속되는 구토, 경련, 심한 흉통",
        ],
        "urgent_action": "red flag 가 하나라도 있으면 약 정보 조회보다 즉시 119·응급실·의료진 연결을 우선하세요.",
        "policy": "이 helper 는 진단이나 복용 지시를 하지 않고, 공식 식약처 안전정보 확인 전에 반드시 되묻기 흐름을 제공합니다.",
    }


EASY_FIELD_MAP = {
    "item_name": "itemName",
    "company_name": "entpName",
    "efficacy": "efcyQesitm",
    "how_to_use": "useMethodQesitm",
    "warnings": "atpnWarnQesitm",
    "cautions": "atpnQesitm",
    "interactions": "intrcQesitm",
    "side_effects": "seQesitm",
    "storage": "depositMethodQesitm",
    "item_seq": "itemSeq",
}

SAFE_STAD_FIELD_MAP = {
    "item_name": "PRDLST_NM",
    "company_name": "BSSH_NM",
    "efficacy": "EFCY_QESITM",
    "how_to_use": "USE_METHOD_QESITM",
    "warnings": "ATPN_WARN_QESITM",
    "cautions": "ATPN_QESITM",
    "interactions": "INTRC_QESITM",
    "side_effects": "SE_QESITM",
}


def normalize_easy_drug_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = {key: summarize_text(item.get(source_key)) for key, source_key in EASY_FIELD_MAP.items()}
    normalized["source"] = "drug_easy_info"
    return normalized


def normalize_safe_stad_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = {key: summarize_text(item.get(source_key)) for key, source_key in SAFE_STAD_FIELD_MAP.items()}
    normalized["source"] = "safe_standby_medicine"
    return normalized


def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
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


def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode({key: value for key, value in params.items() if value not in (None, "")})
    request = urllib.request.Request(f"{url}?{query}", headers={"Accept": "application/json", "User-Agent": "k-skill-mfds/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise ApiError(f"MFDS request failed with HTTP {error.code}", status_code=error.code, url=request.full_url) from error


def lookup_drugs(
    item_names: list[str],
    *,
    service_key: str,
    limit: int = 5,
    request_json: Any = _request_json,
) -> dict[str, Any]:
    normalized_items: list[dict[str, Any]] = []
    for item_name in item_names:
        easy_payload = request_json(
            DRUG_EASY_ENDPOINT,
            {
                "ServiceKey": service_key,
                "pageNo": 1,
                "numOfRows": limit,
                "type": "json",
                "itemName": item_name,
            },
        )
        easy_items = [normalize_easy_drug_item(item) for item in _extract_items(easy_payload)]

        safe_payload = request_json(
            SAFE_STAD_ENDPOINT,
            {
                "serviceKey": service_key,
                "pageNo": 1,
                "numOfRows": limit,
                "type": "json",
                "PRDLST_NM": item_name,
            },
        )
        safe_items = [normalize_safe_stad_item(item) for item in _extract_items(safe_payload)]

        normalized_items.extend(easy_items)
        normalized_items.extend(safe_items)

    return {
        "query": {"item_names": item_names, "limit": limit},
        "items": normalized_items,
        "note": "상호작용 문구는 공식 품목 안내를 그대로 요약한 참고 정보이며, 복용 가능 여부의 최종 판단은 약사·의료진 확인이 필요합니다.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MFDS drug-safety helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    interview = subparsers.add_parser("interview", help="print the mandatory symptom follow-up interview")
    interview.add_argument("--question", default="")
    interview.add_argument("--symptoms", default="")

    lookup = subparsers.add_parser("lookup", help="look up official MFDS drug safety records")
    lookup.add_argument("--item-name", action="append", required=True)
    lookup.add_argument("--service-key")
    lookup.add_argument("--limit", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "interview":
        print(json.dumps(build_drug_interview(question=args.question, symptoms=args.symptoms), ensure_ascii=False, indent=2))
        return 0

    if args.command == "lookup":
        try:
            service_key = resolve_service_key(args.service_key)
            payload = lookup_drugs(args.item_name, service_key=service_key, limit=args.limit)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        except (ValueError, ApiError) as error:
            print(json.dumps({"error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
            return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
