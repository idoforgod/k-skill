# 의약품 안전 체크 가이드

## 이 기능으로 할 수 있는 일

- 식약처 공식 `의약품개요정보(e약은요)` 조회
- 식약처 공식 `안전상비의약품 정보` 조회
- 제품명 기준으로 효능, 사용법, 주의사항, 상호작용, 이상반응, 보관법 요약
- 증상 언급 시 **인터뷰-first** 흐름으로 red flag 확인

## 먼저 필요한 것

- 인터넷 연결
- `python3`
- `DATA_GO_KR_API_KEY`
- 설치된 `mfds-drug-safety` skill 안에 `scripts/mfds_drug_safety.py` helper 포함

> 이 helper 는 증상 질문에 대한 직접 진단을 하지 않는다. 증상이 있으면 바로 단정하지 말고 먼저 되묻는다.

## 공식 표면

- 공공데이터포털 문서: `https://www.data.go.kr/data/15075057/openapi.do`
- e약은요 endpoint: `https://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList`
- 공공데이터포털 문서: `https://www.data.go.kr/data/15097208/openapi.do`
- 안전상비의약품 endpoint: `https://apis.data.go.kr/1471000/SafeStadDrugService/getSafeStadDrugInq`

## 권장 인터뷰 질문

증상이나 복용상황이 있으면 먼저 아래를 확인한다.

- 누가 복용하려는지 (본인/아이/임산부/고령자)
- 어떤 약을 이미 먹었는지 / 지금 먹으려는지
- 언제부터 얼마나 복용했는지
- 현재 증상과 시작 시점
- 복용 중인 다른 약, 기저질환, 알레르기
- 응급 red flag: `호흡곤란`, `의식저하`, `심한 발진`, `지속되는 구토/흉통`

red flag 가 있으면 **즉시 119·응급실·의료진** 안내가 우선이다.

## 기본 흐름

1. `python3 scripts/mfds_drug_safety.py interview ...` 로 되묻기 질문 세트를 준비한다.
2. red flag 가 없고 약 이름이 확인되면 `lookup` 으로 공식 정보를 조회한다.
3. 효능/주의/상호작용/부작용을 짧게 정리한다.
4. `같이 먹어도 되나?` 질문에는 공식 문구를 근거로만 말하고 최종 판단은 약사·의료진 확인이 필요하다고 밝힌다.

## CLI 예시

```bash
python3 scripts/mfds_drug_safety.py interview \
  --question "타이레놀이랑 판콜 같이 먹어도 되나요?" \
  --symptoms "두드러기와 어지러움"
```

```bash
export DATA_GO_KR_API_KEY=your-service-key
python3 scripts/mfds_drug_safety.py lookup --item-name "타이레놀" --item-name "판콜"
```

## 출력 예시 포맷

```json
{
  "query": {
    "item_names": ["타이레놀", "판콜"],
    "limit": 5
  },
  "items": [
    {
      "source": "drug_easy_info",
      "item_name": "타이레놀정160밀리그램",
      "company_name": "한국얀센",
      "efficacy": "감기로 인한 발열 및 동통에 사용합니다.",
      "interactions": "다른 해열진통제와 함께 복용하지 마십시오."
    }
  ]
}
```

## 검증 메모

2026-04-08 기준 로컬에서 아래를 실제 실행해 helper 동작을 확인했다.

- `python3 scripts/mfds_drug_safety.py --help`
- `python3 scripts/mfds_drug_safety.py interview --question "타이레놀이랑 판콜 같이 먹어도 되나요?" --symptoms "두드러기와 어지러움"`
- `DATA_GO_KR_API_KEY` 를 소스한 뒤 live endpoint 호출을 시도해 현재 키/활용승인 상태에서 `HTTP 403` 이 surfaced 되는지 확인

즉, helper 자체와 인터뷰 흐름은 검증했고, live 성공 경로는 해당 서비스 활용승인/키 상태가 준비된 환경에서 바로 이어서 검증할 수 있다.
