# 서울 지하철 도착정보 가이드

## 이 기능으로 할 수 있는 일

- 역 기준 실시간 도착 예정 열차 조회
- 상/하행 또는 외/내선 정보 확인
- 첫 번째/두 번째 도착 메시지 확인

## 먼저 필요한 것

- [공통 설정 가이드](../setup.md) 완료
- [보안/시크릿 정책](../security-and-secrets.md) 확인
- 서울 열린데이터 광장 API key

## 필요한 환경변수

- `SEOUL_OPEN_API_KEY`

### Credential resolution order

1. **이미 환경변수에 있으면** 그대로 사용한다.
2. **에이전트가 자체 secret vault(1Password CLI, Bitwarden CLI, macOS Keychain 등)를 사용 중이면** 거기서 꺼내 환경변수로 주입해도 된다.
3. **`~/.config/k-skill/secrets.env`** (기본 fallback) — plain dotenv 파일, 퍼미션 `0600`.
4. **아무것도 없으면** 유저에게 물어서 2 또는 3에 저장한다.

## 입력값

- 역명
- 선택 사항: 가져올 건수

## 기본 흐름

1. `SEOUL_OPEN_API_KEY` 가 없으면 credential resolution order에 따라 확보합니다.
3. 역명 기준으로 실시간 도착정보를 조회합니다.
4. 호선, 진행 방향, 도착 메시지, 조회 시점을 함께 요약합니다.

## 예시

```bash
curl -s "http://swopenAPI.seoul.go.kr/api/subway/${SEOUL_OPEN_API_KEY}/json/realtimeStationArrival/0/8/강남"
```

## 주의할 점

- 실시간 데이터라 몇 초 단위로 바뀔 수 있습니다.
- 역명 표기가 다르면 결과가 비어 있을 수 있습니다.
- 일일 호출 제한이나 quota 초과 가능성이 있습니다.
