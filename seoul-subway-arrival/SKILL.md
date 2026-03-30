---
name: seoul-subway-arrival
description: Look up Seoul real-time subway arrival information with the official Seoul Open Data API. Use when the user asks when a train arrives, which trains are approaching a station, or how crowded Seoul subway timing looks right now.
license: MIT
metadata:
  category: transit
  locale: ko-KR
  phase: v1
---

# Seoul Subway Arrival

## What this skill does

서울 열린데이터 광장의 실시간 지하철 도착정보 Open API로 역 기준 도착 예정 열차 정보를 요약한다.

## When to use

- "강남역 지금 몇 분 뒤 도착해?"
- "서울역 1호선 도착 정보 보여줘"
- "잠실역 곧 들어오는 열차 정리해줘"

## Prerequisites

- 서울 열린데이터 광장 API key
- optional: `jq`

## Required environment variables

- `SEOUL_OPEN_API_KEY`

### Credential resolution order

1. **이미 환경변수에 있으면** 그대로 사용한다.
2. **에이전트가 자체 secret vault(1Password CLI, Bitwarden CLI, macOS Keychain 등)를 사용 중이면** 거기서 꺼내 환경변수로 주입해도 된다.
3. **`~/.config/k-skill/secrets.env`** (기본 fallback) — plain dotenv 파일, 퍼미션 `0600`.
4. **아무것도 없으면** 유저에게 물어서 2 또는 3에 저장한다.

기본 경로에 저장하는 것은 fallback일 뿐, 강제가 아니다.

## Inputs

- 역명
- 선택 사항: 가져올 건수

## Workflow

### 1. Ensure credentials are available

`SEOUL_OPEN_API_KEY` 환경변수가 설정되어 있는지 확인한다. 없으면 위 credential resolution order에 따라 확보한다.

시크릿이 없다는 이유로 비공식 미러 API나 다른 출처로 자동 우회하지 않는다.

### 2. Query the official station arrival endpoint

서울 실시간 지하철 API는 역명 기준 실시간 도착 정보를 JSON/XML로 제공한다. 기본 질의 예시는 다음 패턴을 쓴다.

```bash
curl -s "http://swopenAPI.seoul.go.kr/api/subway/${SEOUL_OPEN_API_KEY}/json/realtimeStationArrival/0/8/강남"
```

### 3. Summarize the response

가능하면 아래 항목만 먼저 요약한다.

- 호선
- 상/하행 또는 외/내선
- 첫 번째 도착 메시지
- 두 번째 도착 메시지
- 도착 예정 시간(있으면 초 단위)

### 4. Be conservative about live data

실시간 데이터는 몇 초 단위로 바뀔 수 있으므로, 답변에는 조회 시점을 같이 적는다.

## Done when

- 요청 역의 도착 예정 열차가 정리되어 있다
- live data 기준 시점이 명시되어 있다
- key가 노출되지 않았다

## Failure modes

- API key 미설정
- quota 초과
- 역명 표기 불일치

## Notes

- 서울 열린데이터 광장 가이드는 실시간 지하철 Open API에 일일 호출 제한이 있을 수 있다고 안내한다
- endpoint path는 API 버전 변경 가능성이 있으므로 실패 시 dataset console의 최신 샘플 URL을 다시 확인한다
