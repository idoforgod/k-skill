---
name: mfds-food-safety
description: 식약처/식품안전나라 공개 표면으로 식품 회수·부적합 정보를 조회하기 전에 증상·섭취상황을 반드시 되묻는 인터뷰형 식품 안전 체크 스킬.
license: MIT
metadata:
  category: public-health
  locale: ko-KR
  phase: v1
---

# 식품 안전 체크

## What this skill does

식약처/식품안전나라 공개 표면으로 **부적합 식품 목록**과 **회수·판매중지 공개 목록**을 확인한다.

하지만 사용자가 복통, 설사, 발진 같은 증상을 말하면 **바로 단정하지 말고 먼저 되묻는다.**

- 누가 먹었는지 (본인/아이/임산부/고령자)
- 무엇을 언제 얼마나 먹었는지
- 같이 먹은 음식/술/약
- 현재 증상과 시작 시점
- 기저질환, 임신, 알레르기
- red flag (`혈변`, `탈수`, `호흡곤란`, `의식저하`, `심한 복통/고열`)

red flag 가 있으면 식품 조회보다 **즉시 응급실·119·의료진 안내**가 우선이다.

## When to use

- "이 음식 먹어도 괜찮니?"
- "이 김밥 먹고 배가 아픈데 회수 이력 있나?"
- "식약처 공식 부적합 식품 목록에서 제품명 확인해줘"
- "식품안전나라 공개 회수 목록에서 업체명으로 찾아줘"

## Prerequisites

- 인터넷 연결
- `python3`
- 부적합 식품 live 조회용 `DATA_GO_KR_API_KEY` (공공데이터포털)
- 회수정보 smoke/demo 용 `--sample-recalls` 또는 식품안전나라 API key
- 설치된 skill payload 안에 `scripts/mfds_food_safety.py` helper 포함

## Mandatory interview first

증상/섭취상황이 언급되면 결론을 말하기 전에 먼저 되묻는다.

권장 첫 질문 예시:

- `누가 무엇을 언제 얼마나 먹었는지, 지금 복통/구토/설사/발진 같은 증상이 있는지 먼저 알려주세요.`
- `호흡곤란, 혈변, 심한 탈수, 의식저하, 심한 복통/고열이 있으면 즉시 응급실이나 119가 우선입니다.`

## Official surfaces

- 공공데이터포털 문서: `https://www.data.go.kr/data/15056516/openapi.do`
- 부적합 식품 endpoint: `https://apis.data.go.kr/1471000/PrsecImproptFoodInfoService03/getPrsecImproptFoodList01`
- 식품안전나라 회수·판매중지 문서: `https://www.data.go.kr/data/15074318/openapi.do`
- 식품안전나라 API 안내: `https://www.foodsafetykorea.go.kr/api/openApiInfo.do?menu_grp=MENU_GRP31&menu_no=661&show_cnt=10&start_idx=1&svc_no=I0490&svc_type_cd=API_TYPE06`
- 식품안전나라 회수 sample: `https://openapi.foodsafetykorea.go.kr/api/sample/I0490/json/1/5`

## Workflow

1. 증상/섭취상황이 있으면 인터뷰를 먼저 진행한다.
2. red flag 가 있으면 즉시 응급 안내로 전환한다.
3. `PrsecImproptFoodInfoService03/getPrsecImproptFoodList01` 로 부적합 식품 목록을 가져와 제품명/업체명 기준으로 로컬 필터링한다.
4. 필요하면 식품안전나라 `I0490` 회수 sample/live 목록도 함께 확인한다.
5. 제품명, 업체명, 회수/부적합 사유, 공개일자를 짧게 정리하고, 먹어도 되는지 단정하지 않는다.

## CLI examples

```bash
python3 scripts/mfds_food_safety.py interview \
  --question "이 김밥 먹어도 되나요?" \
  --symptoms "복통과 설사"
```

```bash
python3 scripts/mfds_food_safety.py search --query "김밥" --sample-recalls --limit 5
```

```bash
export DATA_GO_KR_API_KEY=your-service-key
python3 scripts/mfds_food_safety.py search --query "김밥" --limit 5
```

## Response policy

- 이 스킬은 **직접 진단**을 하지 않는다.
- 이 스킬은 **식중독 진단**이나 **섭취 허가/금지의 최종 판정**을 하지 않는다.
- 공식 공개 목록에 있는 사실만 전달한다.
- 증상이 있는 질문은 인터뷰 없이 바로 답하지 않는다.
- red flag 또는 고위험군이면 의료진 상담을 우선 권고한다.

## Done when

- 증상 또는 섭취상황을 먼저 되물었다.
- red flag 여부를 확인했다.
- 공식 공개 목록에서 제품명 또는 업체명 기준 결과를 최소 1건 이상 찾았거나, 없다고 분명히 알렸다.
- 제품명, 업체명, 공개사유/부적합 사유, 공개일자를 포함한 요약을 제공했다.
