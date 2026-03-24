---
name: kbo-results
description: Fetch KBO game schedules and results for a specific date with the kbo-game npm package. Use when the user asks for today's KBO games, yesterday's scores, or a date-specific scoreboard.
license: MIT
metadata:
  category: sports
  locale: ko-KR
  phase: v1
---

# KBO Results

## What this skill does

`kbo-game` 패키지로 특정 날짜 KBO 경기 정보를 가져와 경기 일정, 스코어, 상태를 요약한다.

## When to use

- "오늘 KBO 경기 결과 알려줘"
- "어제 한화 경기 스코어 보여줘"
- "2026-04-01 KBO 일정 정리해줘"

## Prerequisites

- Node.js 18+
- `npm install kbo-game`

## Inputs

- 날짜: `YYYY-MM-DD`
- 선택 사항: 특정 팀명

## Workflow

### 1. Fetch the date

```bash
node --input-type=module - <<'JS'
import { getGameInfo } from "kbo-game";

const date = "2026-03-25";
const games = await getGameInfo(date);
console.log(JSON.stringify(games, null, 2));
JS
```

### 2. Normalize for humans

원본 데이터를 그대로 던지지 말고 아래 기준으로 정리한다.

- 홈팀 vs 원정팀
- 진행 상태 또는 경기 종료 여부
- 스코어
- 필요한 경우 특정 팀만 필터링

### 3. Keep the answer compact

사용자가 scoreboard를 원하면 경기별 한 줄 요약부터 준다.

## Done when

- 날짜 기준 전체 경기 요약이 있다
- 팀 필터 요청이면 해당 팀 경기만 남아 있다
- raw JSON이 필요하면 별도로 제공할 수 있다

## Failure modes

- KBO 사이트 변경으로 패키지 응답이 깨질 수 있다
- 비시즌 날짜는 빈 결과가 올 수 있다

## Notes

- 이 스킬은 조회 전용이다
- 사용자 기준 "오늘/어제" 같은 상대 날짜는 항상 절대 날짜로 변환해서 실행한다
