# 새 스킬 추가 가이드

새 스킬을 k-skill에 추가하는 방법과 스킬이 동작하는 구조를 설명한다.

---

## 스킬이란

스킬은 AI 에이전트(Claude Code 등)가 특정 작업을 수행하는 방법을 정의한 문서+코드 묶음이다. 에이전트는 `SKILL.md`를 읽고 거기 적힌 워크플로우를 따라 실행한다.

스킬에는 네 가지 구현 유형이 있다.

| 유형 | 설명 | 예시 |
|------|------|------|
| **SKILL.md 전용** | 문서만으로 동작 (에이전트가 bash/python 직접 실행) | `kakaotalk-mac`, `srt-booking` |
| **npm 패키지** | `packages/` 아래 Node.js 라이브러리로 구현 | `k-lotto`, `blue-ribbon-nearby` |
| **프록시 경유** | `k-skill-proxy`가 upstream API 키를 보관하고 HTTP로 중계 | `seoul-subway-arrival`, `fine-dust-location` |
| **Python 스크립트** | `scripts/`의 Python 파일 직접 실행 | `korean-spell-check`, `sillok-search` |

---

## 스킬의 구조

모든 스킬은 **저장소 루트에 디렉토리 하나**를 갖는다.

```
k-skill/
├── my-new-skill/          ← 스킬 디렉토리 (이름 = 스킬 이름)
│   ├── SKILL.md           ← 필수. 에이전트가 읽는 핵심 파일
│   └── (지원 파일들)       ← 선택. 스크립트, 데이터 등
├── packages/              ← npm 패키지 유형일 때만
│   └── my-new-skill/
│       ├── package.json
│       ├── src/
│       └── test/
└── scripts/               ← Python 스크립트 유형일 때만
    └── my_new_skill.py
```

---

## SKILL.md 형식

`SKILL.md`는 YAML frontmatter + Markdown 본문으로 구성된다.

```markdown
---
name: my-new-skill
description: 한 문장으로 이 스킬이 무엇을 하는지 설명한다. 에이전트 UI에 표시된다.
license: MIT
metadata:
  category: utility
  locale: ko-KR
  phase: v1
---

# My New Skill

## What this skill does

이 스킬이 무엇을 하는지 한두 문단으로 설명한다.

## When to use

- "사용자가 이런 말을 할 때"
- "또는 이런 상황일 때"

## Prerequisites

- Node.js 18+ (필요하면)
- 패키지 설치 명령

## Workflow

### 1. 첫 번째 단계

설명과 실행할 코드를 적는다.

```bash
# 실행할 명령어
```

### 2. 두 번째 단계

...

## Done when

- 이런 조건이 만족되면 완료다

## Failure modes

- 예상 가능한 실패 상황

## Notes

- 특이사항, 보안 정책 등
```

### frontmatter 필드

| 필드 | 필수 | 설명 |
|------|------|------|
| `name` | ✅ | **디렉토리 이름과 정확히 일치**해야 한다 |
| `description` | ✅ | 에이전트 UI 표시용 한 줄 설명 |
| `license` | ✅ | 항상 `MIT` |
| `metadata.category` | ✅ | `utility` / `transit` / `travel` / `messaging` / `legal` / `setup` 등 |
| `metadata.locale` | ✅ | `ko-KR` |
| `metadata.phase` | ✅ | `v1` (안정) / `v1.5` (기능 추가 중) |

---

## 유형별 구현 방법

### A. SKILL.md 전용 스킬

에이전트가 `SKILL.md` 안의 bash/python 코드를 직접 실행한다.

1. 디렉토리 생성: `mkdir my-new-skill`
2. `my-new-skill/SKILL.md` 작성
3. Workflow 섹션에 에이전트가 따를 단계별 명령어를 적는다

외부 라이브러리나 서버 없이 동작해야 한다.

### B. npm 패키지 스킬

`packages/my-new-skill/`에 Node.js 구현체를 만들고, 루트 디렉토리 `my-new-skill/SKILL.md`에서 `require('my-new-skill')`로 호출한다.

```
packages/my-new-skill/
├── package.json    # name, version, main, exports 필수
├── README.md
├── src/
│   └── index.js
└── test/
    └── index.test.js
```

`package.json`에 `"name": "my-new-skill"` 설정 후 루트 `package.json`의 `workspaces`에 등록한다.

npm에 배포하려면 `.changeset/` 파일을 추가한다 (`docs/releasing.md` 참고).

### C. 프록시 경유 스킬

upstream API 키를 사용자에게 노출하지 않으려면 `k-skill-proxy`를 경유한다.

1. `packages/k-skill-proxy/src/server.js`에 새 route 추가
2. `SKILL.md` Workflow에 `curl $KSKILL_PROXY_BASE_URL/v1/...` 형태로 호출 작성
3. upstream API 키는 서버의 `~/.config/k-skill/secrets.env`에만 보관

프록시 서버는 main 브랜치에 merge되어야 프로덕션에 반영된다 (`CLAUDE.md` 참고).

### D. Python 스크립트 스킬

`scripts/my_skill.py`를 만들고 `SKILL.md`에서 `python3 scripts/my_skill.py`로 호출한다.

---

## 스킬 등록 & 검증

스킬은 **별도 레지스트리 없이 디렉토리 스캔으로 자동 발견**된다.

추가 후 검증:

```bash
npm run ci
```

이 명령은 `scripts/validate-skills.sh`를 실행해 다음을 확인한다.

- 루트 하위 모든 디렉토리에 `SKILL.md`가 있는지
- frontmatter가 `---`로 시작하는지
- `name` 필드가 있는지
- `description` 필드가 있는지
- `name` 필드 값이 디렉토리 이름과 일치하는지

---

## 시크릿이 필요한 스킬

인증이 필요한 스킬은 아래 우선순위로 credential을 확보한다.

1. 이미 환경변수에 있으면 → 그대로 사용
2. 에이전트 vault(1Password, Bitwarden, macOS Keychain) → 주입
3. `~/.config/k-skill/secrets.env` → 파일에서 읽기
4. 아무것도 없으면 → 사용자에게 물어보고 3번에 저장

시크릿 변수 이름 규칙: `KSKILL_<서비스명>_<항목>` (예: `KSKILL_SRT_ID`)

절대 하지 말 것:
- 시크릿을 저장소에 커밋
- 프록시 upstream 키를 클라이언트에 노출
- 사용자 확인 없이 side-effect가 있는 작업 실행

---

## 체크리스트

새 스킬을 PR 올리기 전에 확인한다.

- [ ] `my-new-skill/SKILL.md` 작성 완료
- [ ] frontmatter `name`이 디렉토리 이름과 일치
- [ ] `npm run ci` 통과 (`./scripts/validate-skills.sh` 포함)
- [ ] npm 패키지라면 `packages/`에 구현체와 테스트 추가
- [ ] npm 패키지라면 `.changeset/*.md` 파일 추가 (반드시 **기능 PR에서**, Version Packages PR에서 추가하지 말 것)
- [ ] 프록시 경유라면 `k-skill-proxy/src/server.js`에 route 추가하고 main에 merge
- [ ] 시크릿이 있다면 `KSKILL_` 접두사 규칙 준수 및 `docs/setup.md` 업데이트
- [ ] `docs/features/my-new-skill.md` 작성 (선택, 상세 가이드)

---

## 관련 문서

- [공통 설정 가이드](setup.md) — 시크릿 설정 방법
- [릴리스와 자동 배포](releasing.md) — npm 패키지 배포 흐름
- [보안/시크릿 정책](security-and-secrets.md) — 인증 정보 취급 원칙
