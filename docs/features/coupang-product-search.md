# 쿠팡 상품 가격/리뷰 조회 가이드

## 이 기능으로 할 수 있는 일

- 쿠팡 공식 검색 URL 만들기
- 브라우저에서 캡처한 쿠팡 검색 결과 HTML 파싱
- 상품 상세/가격/판매자/배송 배지/필수 표기 정보 파싱
- 상품 리뷰 요약과 개별 리뷰 파싱
- direct fetch / headless browser 가 차단되는지 probe

## 먼저 알아둘 점

2026-03-31 기준 확인 내용:

- 쿠팡 개발자 Open API 문서는 **판매자/WING 중심**이다.
- 일반 소비자용 상품 검색·상품평 조회 Open API는 확인하지 못했다.
- 이 저장소 환경에서 `www.coupang.com` direct fetch 는 `403 Access Denied` 였다.
- `m.coupang.com` direct fetch 도 차단되었지만, rerun 마다 `200 challenge-html` 또는 `403 access-denied-html` 처럼 **차단 응답 status/reason 이 달라질 수 있었다.**
- headless Playwright-core probe 도 막혔고, 여기서도 **exact blocked shape 는 edge/challenge 상태에 따라 달라질 수 있었다.**

즉, 이 기능은 **anti-bot 우회**가 아니라 다음 흐름을 기준으로 동작한다.

1. 공식 쿠팡 URL을 만든다.
2. 가능하면 브라우저 세션에서 확보한 HTML 을 파싱한다.
3. 막히면 probe 결과를 그대로 보여주고, 브라우저 HTML 또는 상품 URL을 추가 입력으로 받는다.

## 공식 표면

- seller Open API docs: `https://developers.coupangcorp.com/hc/ko/sections/360004260614-상품-API`
- desktop search: `https://www.coupang.com/np/search?q=<query>`
- mobile search: `https://m.coupang.com/nm/search?q=<query>`
- product detail: `https://www.coupang.com/vp/products/<productId>?itemId=<itemId>&vendorItemId=<vendorItemId>`
- review anchor: `#sdpReview`

## 기본 흐름

1. 검색어 또는 상품 URL을 받는다.
2. `probeAutomation()` 으로 이 환경에서 direct/headless 접근이 가능한지 본다.
3. 브라우저 HTML 이 있으면 `searchProducts()` 로 후보를 정리한다.
4. 같은 방식으로 `getProductDetail()` 과 `getProductReviews()` 를 호출한다.
5. 차단되면 `현재 환경에서는 쿠팡 anti-bot 에 막혀 브라우저 HTML 이 필요하다`고 답한다.

## Node.js 예시

```js
const {
  getProductDetail,
  getProductReviews,
  probeAutomation,
  searchProducts
} = require("coupang-product-search")

async function browserCapture(url) {
  // 호출 환경에서 구현
  throw new Error(`Implement browser capture for ${url}`)
}

async function main() {
  const probe = await probeAutomation("생수")
  console.log(probe)
  // browser 결과는 browserFetchHtml 을 주입하지 않으면 null 이다.

  const search = await searchProducts("생수", { fetchHtml: browserCapture })
  console.log(search.items.slice(0, 3))

  const detail = await getProductDetail(search.items[0].productUrl, { fetchHtml: browserCapture })
  console.log(detail)

  const reviews = await getProductReviews(detail.productUrl, { fetchHtml: browserCapture })
  console.log(reviews.summary)
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
```

## Live probe 메모

아래 값은 **2026-03-31** 기준 `query=생수` 로 확인한 blocked outcome 범위다.

```json
{
  "directDesktop": {
    "blocked": true,
    "observed": ["403/access-denied-html"]
  },
  "directMobile": {
    "blocked": true,
    "observed": ["200/challenge-html", "403/access-denied-html"]
  },
  "browser": {
    "blocked": true,
    "observed": ["access-denied-html"],
    "notes": "browserFetchHtml 을 주입한 수동/외부 Playwright-core 검증 기준"
  }
}
```

즉, **차단 자체는 확인되지만 exact status/reason 은 달라질 수 있고, clean checkout 의 `probeAutomation(\"생수\")` 는 browser 값을 자동으로 채우지 않는다.** 공식 URL 구조 자체는 안정적으로 만들 수 있었지만, live HTML 수집은 환경 의존적이다.

## 운영 팁

- 검색어가 넓으면 용도/예산/브랜드/용량을 먼저 물어본다.
- 리뷰는 평균 평점, 총 리뷰 수, 대표 리뷰 2~3개만 먼저 요약한다.
- 상품 URL이 이미 있으면 검색 단계를 건너뛰고 상세/리뷰 파싱으로 바로 들어간다.
- headless probe 가 막히면 우회 시도를 늘리지 말고 브라우저 캡처 HTML 필요 사실을 분명히 말한다.
