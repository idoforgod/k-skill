# 한국 부동산 실거래가 조회 가이드

## 이 기능으로 할 수 있는 일

- 아파트 매매 실거래가 조회 (`get_apartment_trades`)
- 아파트 전월세 조회 (`get_apartment_rent`)
- 오피스텔/연립다세대/단독주택/상업업무용 실거래가 조회
- 지역코드 조회 (`get_region_code`) 후 행정구역 기준 검색
- 청약홈 도구 연결
- 온비드 코드/주소 조회
- 온비드 입찰결과 도구 (`get_public_auction_items`, `get_public_auction_item_detail`)는 upstream README 기준 `⚠️ WIP` 상태로 preview 안내
- hosted endpoint가 없을 때 self-host + Cloudflare Tunnel + launchd 운영

## 가장 중요한 규칙

이 기능은 upstream **`real-estate-mcp`**(`https://github.com/tae0y/real-estate-mcp/tree/main`)를 그대로 사용한다.
이 저장소에는 원본 MCP 서버 코드를 넣지 않고, 스킬 문서와 연결 가이드만 유지한다.

2026-04-05 기준 upstream README/docs에는 고정 public MCP URL이 문서화돼 있지 않았다.
그래서 기본 문서는 **로컬 stdio 연결 또는 self-host HTTP 운영**을 기준으로 적는다.

## 먼저 필요한 것

- 인터넷 연결
- `uv`
- 공공데이터포털 API key (`DATA_GO_KR_API_KEY`)
- upstream clone: `git clone https://github.com/tae0y/real-estate-mcp.git`
- shared HTTP가 필요하면 Docker + Cloudflare Tunnel

`DATA_GO_KR_API_KEY` 하나만 넣어도 기본 실거래가 조회는 시작할 수 있다.
청약홈/온비드를 더 세밀하게 나누고 싶으면 upstream 문서대로 `ODCLOUD_API_KEY`, `ODCLOUD_SERVICE_KEY`, `ONBID_API_KEY` 를 추가한다.
다만 `get_public_auction_items`, `get_public_auction_item_detail` 는 2026-04-05 기준 upstream README 에서 아직 `⚠️ WIP` 로 남아 있으므로, 안정 기능처럼 소개하지 말고 preview/실험 단계로만 설명한다.

## 가장 빠른 시작: Codex CLI stdio

```bash
git clone https://github.com/tae0y/real-estate-mcp.git
cd real-estate-mcp

codex mcp add real-estate \
  --env DATA_GO_KR_API_KEY=your_api_key_here \
  -- uv run --directory /path/to/real-estate-mcp \
  python src/real_estate/mcp_server/server.py

codex mcp list
codex mcp get real-estate
```

## Claude Desktop stdio 예시

```json
{
  "mcpServers": {
    "real-estate": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/real-estate-mcp",
        "python", "src/real_estate/mcp_server/server.py"
      ],
      "env": {
        "DATA_GO_KR_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

## shared HTTP / self-host 운영

고정 hosted endpoint를 확인하지 못했다면 아래 흐름으로 self-host 한다.

### 1. upstream Docker compose 시작

```bash
git clone https://github.com/tae0y/real-estate-mcp.git
cd real-estate-mcp
cp .env.example .env
printf 'DATA_GO_KR_API_KEY=your_api_key_here\n' >> .env
REPOSITORY_ROOT=$(pwd)
docker compose -f "$REPOSITORY_ROOT"/docker/docker-compose.yml up -d --build
```

### 2. MCP initialize로 health check

```bash
curl -s -X POST http://localhost/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.1"}}}'
```

정상이라면 응답 JSON 안에 `protocolVersion` 이 보인다.

### 3. Cloudflare Tunnel로 공유 도메인 만들기

```bash
cloudflared tunnel login
cloudflared tunnel create real-estate-mcp
cloudflared tunnel route dns real-estate-mcp real-estate-mcp.example.com
cat > ~/.cloudflared/config.yml <<'EOF'
tunnel: real-estate-mcp
credentials-file: /Users/YOUR_USER/.cloudflared/<tunnel-id>.json
ingress:
  - hostname: real-estate-mcp.example.com
    service: http://localhost:80
  - service: http_status:404
EOF
cloudflared tunnel run real-estate-mcp
```

그 다음 MCP URL은 `https://real-estate-mcp.example.com/mcp` 로 잡는다.
인터넷에 공개한다면 upstream OAuth 문서(`docs/setup-oauth.md`)대로 `AUTH_MODE=oauth` 와 Auth0/클라이언트 시크릿을 붙인다.

### 4. launchd로 자동 실행

macOS 기준으로는 **launchd 를 tunnel 전용으로만** 쓰고, upstream 서버 컨테이너 재시작은 Docker 쪽에 맡긴다.
upstream `docker/docker-compose.yml` 이 이미 `restart: unless-stopped` 를 설정하므로, `docker compose -f docker/docker-compose.yml up -d` 를 `RunAtLoad` + `KeepAlive` launchd job 에 넣으면 daemonize 직후 종료된 프로세스를 launchd 가 계속 다시 띄우는 restart loop가 생긴다.

따라서 서버 쪽은 Docker Desktop/Engine 자동 시작을 켜고 `docker compose ... up -d --build` 를 한 번 실행해 둔 뒤, `cloudflared tunnel run real-estate-mcp` 만 launchd 에 등록한다.

- `~/Library/LaunchAgents/com.kskill.real-estate-mcp.tunnel.plist`

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.kskill.real-estate-mcp.tunnel.plist
launchctl enable gui/$(id -u)/com.kskill.real-estate-mcp.tunnel
```

## 조회 흐름 권장 순서

1. 주소/행정구역이 애매하면 `get_region_code` 부터 호출한다.
2. 아파트 매매면 `get_apartment_trades`, 전월세면 `get_apartment_rent` 를 쓴다.
3. 오피스텔/빌라/단독주택/상업업무용은 해당 전용 tool로 분기한다.
4. 사용자가 연월을 안 줬으면 기준 월을 먼저 확인한다.
5. 실거래가와 호가를 섞지 말고, 신고 기반 데이터라는 점을 짧게 명시한다.
6. public endpoint가 미리 없다면 self-host + Cloudflare Tunnel + launchd 경로를 그대로 제시한다.

## 라이브 확인 메모

2026-04-05 기준 로컬 smoke verification 에서 upstream 저장소로 아래 bootstrap 명령을 실제 실행해 진입 가능 여부를 확인했다.

- `uv sync`
- `uv run real-estate-mcp --help`
- `DATA_GO_KR_API_KEY=dummy uv run real-estate-mcp --transport http --host 127.0.0.1 --port 8017`
- `curl -s -X POST http://127.0.0.1:8017/mcp ... initialize` → `protocolVersion: 2024-11-05`

즉, upstream 프로젝트 자체는 로컬에서 실행 가능한 상태로 확인했다. 실제 거래 데이터 조회는 유효한 `DATA_GO_KR_API_KEY` 가 준비된 환경에서 바로 이어서 검증하면 된다.

## 참고 링크

- 원본 MCP 서버: `https://github.com/tae0y/real-estate-mcp/tree/main`
- Codex CLI 가이드: `https://github.com/tae0y/real-estate-mcp/blob/main/docs/setup-codex-cli.md`
- Docker 가이드: `https://github.com/tae0y/real-estate-mcp/blob/main/docs/setup-docker.md`
- OAuth 가이드: `https://github.com/tae0y/real-estate-mcp/blob/main/docs/setup-oauth.md`
