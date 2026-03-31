# coupang-product-search

쿠팡 공식 쇼핑 URL(`검색`, `상품 상세`, `리뷰`)을 만들고, **브라우저 세션에서 캡처한 HTML** 을 파싱해 상품 후보/가격/상세/리뷰를 정규화하는 Node.js 패키지입니다.

## 왜 이런 형태인가

2026-03-31 기준으로 확인한 결과:

- official developer docs (seller/Open API docs): `https://developers.coupangcorp.com/hc/ko`
- 쿠팡 개발자 Open API 문서는 판매자/WING 중심이며, **일반 소비자용 상품 검색·상품평 조회 Open API는 확인되지 않았습니다.**
- 이 저장소 환경에서 `https://www.coupang.com/np/search?q=생수` 직접 요청은 **403 Access Denied** 였습니다.
- 같은 날짜에 `https://m.coupang.com/nm/search?q=생수` 직접 요청도 **차단된 HTML** 이었고, 재실행마다 `200 challenge-html` 또는 `403 access-denied-html` 처럼 **정확한 status/reason 이 달라질 수 있었습니다.**
- 같은 날짜에 `m.coupang.com` 대상 **headless Playwright-core probe** 도 차단되었고, **blocked shape 역시 edge/challenge 상태에 따라 달라질 수 있었습니다.**

그래서 이 패키지는 **우회 로직** 대신 아래 두 가지를 제공합니다.

1. 공식 Coupang URL builder (`search`, `product`, `review anchor`)
2. 브라우저에서 얻은 HTML을 파싱하는 dependency-light parser/client

## 확인한 공식 표면

- seller Open API docs: `https://developers.coupangcorp.com/hc/ko/sections/360004260614-상품-API`
- desktop search: `https://www.coupang.com/np/search?q=<query>`
- mobile search: `https://m.coupang.com/nm/search?q=<query>`
- product detail: `https://www.coupang.com/vp/products/<productId>?itemId=<itemId>&vendorItemId=<vendorItemId>`
- review anchor: `#sdpReview`

## 설치

배포 후:

```bash
npm install coupang-product-search
```

이 저장소에서 개발할 때:

```bash
npm install
```

## 공개 API

- `buildSearchUrl(query, options?)`
- `buildProductUrl(request)`
- `buildReviewsUrl(request)`
- `parseSearchResultsHtml(html, context?)`
- `parseProductDetailHtml(html, context?)`
- `parseReviewsHtml(html, context?)`
- `searchProducts(query, { fetchHtml })`
- `getProductDetail(request, { fetchHtml })`
- `getProductReviews(request, { fetchHtml })`
- `probeAutomation(query, { fetchImpl?, browserFetchHtml? })`

## 사용 예시

```js
const {
  getProductDetail,
  getProductReviews,
  probeAutomation,
  searchProducts
} = require("coupang-product-search")

async function fetchHtmlFromBrowser(url) {
  // 이 부분은 호출 환경이 채워야 합니다.
  // 예: 이미 열려 있는 브라우저 세션, 수동 저장 HTML, 통과 가능한 Playwright runner 등
  throw new Error(`Implement browser capture for ${url}`)
}

async function main() {
  const probe = await probeAutomation("생수")
  console.log(probe)
  // clean checkout 에서는 browser === null 입니다.
  // browser 결과를 보려면 browserFetchHtml(url) 주입이 필요합니다.

  const search = await searchProducts("생수", { fetchHtml: fetchHtmlFromBrowser })
  console.log(search.items[0])

  const detail = await getProductDetail(search.items[0].productUrl, {
    fetchHtml: fetchHtmlFromBrowser
  })
  console.log(detail)

  const reviews = await getProductReviews(detail.productUrl, {
    fetchHtml: fetchHtmlFromBrowser
  })
  console.log(reviews.summary)
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
```

## Live probe notes

2026-03-31 기준 `query=생수` 로 확인한 blocked outcome 메모:

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
    "notes": "manual browserFetchHtml / Playwright-core runner 를 주입한 별도 검증 기준"
  }
}
```

즉, **막힌다는 사실은 재현되더라도 exact status/reason 은 rerun, edge, challenge 상태에 따라 달라질 수 있습니다.** 공식 URL 구조와 HTML 파서는 유지하되, live HTML 확보는 호출 환경의 실제 브라우저 세션/권한에 따라 달라집니다.
