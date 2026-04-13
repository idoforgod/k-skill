const DATA_GO_KR_UPSTREAM_BASE_URL = "https://apis.data.go.kr";
const DRUG_EASY_ENDPOINT = `${DATA_GO_KR_UPSTREAM_BASE_URL}/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList`;
const SAFE_STAD_ENDPOINT = `${DATA_GO_KR_UPSTREAM_BASE_URL}/1471000/SafeStadDrugService/getSafeStadDrugInq`;
const IMPROPER_FOOD_ENDPOINT = `${DATA_GO_KR_UPSTREAM_BASE_URL}/1471000/PrsecImproptFoodInfoService03/getPrsecImproptFoodList01`;
const FOOD_RECALL_SAMPLE_URL = "https://openapi.foodsafetykorea.go.kr/api/sample/I0490/json/{start}/{end}";
const FOOD_RECALL_LIVE_URL = "https://openapi.foodsafetykorea.go.kr/api/{apiKey}/I0490/json/{start}/{end}";

class ProxyError extends Error {
  constructor(message, { code = "proxy_error", statusCode = 502 } = {}) {
    super(message);
    this.code = code;
    this.statusCode = statusCode;
  }
}

function trimOrNull(value) {
  if (value === undefined || value === null) {
    return null;
  }

  const trimmed = String(value).trim();
  return trimmed ? trimmed : null;
}

function summarizeText(value) {
  if (value === undefined || value === null) {
    return "";
  }

  return String(value)
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function parsePositiveInteger(value, fallback, { fieldName, min = 1, max = 50 } = {}) {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }

  const parsed = Number.parseInt(String(value), 10);
  if (!Number.isFinite(parsed) || parsed < min || parsed > max) {
    throw new Error(`${fieldName} must be an integer between ${min} and ${max}.`);
  }

  return parsed;
}

function normalizeStringList(value) {
  if (Array.isArray(value)) {
    return value.flatMap((item) => normalizeStringList(item));
  }

  const trimmed = trimOrNull(value);
  return trimmed ? [trimmed] : [];
}

function normalizeMfdsDrugLookupQuery(query) {
  const itemNames = [
    ...normalizeStringList(query.itemName),
    ...normalizeStringList(query.item_name)
  ];
  const uniqueItemNames = [...new Set(itemNames)];

  if (uniqueItemNames.length === 0) {
    throw new Error("Provide at least one itemName.");
  }

  return {
    itemNames: uniqueItemNames,
    limit: parsePositiveInteger(query.limit, 5, { fieldName: "limit", min: 1, max: 20 })
  };
}

function normalizeMfdsFoodSafetyQuery(query) {
  const q = trimOrNull(query.query ?? query.q);
  if (!q) {
    throw new Error("Provide query.");
  }

  return {
    query: q,
    limit: parsePositiveInteger(query.limit, 10, { fieldName: "limit", min: 1, max: 20 })
  };
}

async function requestJson(url, { params, fetchImpl = global.fetch } = {}) {
  if (typeof fetchImpl !== "function") {
    throw new ProxyError("A fetch implementation is required.");
  }

  const requestUrl = new URL(url);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        requestUrl.searchParams.set(key, String(value));
      }
    }
  }

  let response;
  try {
    response = await fetchImpl(requestUrl.toString(), {
      headers: {
        accept: "application/json",
        "user-agent": "k-skill-proxy/1.0"
      }
    });
  } catch (error) {
    throw new ProxyError(error.message);
  }

  const text = await response.text();
  if (!response.ok) {
    throw new ProxyError(`Upstream responded with ${response.status}`, {
      code: "upstream_error"
    });
  }

  try {
    return JSON.parse(text);
  } catch (error) {
    if (requestUrl.hostname === "openapi.foodsafetykorea.go.kr") {
      throw new ProxyError(
        "FoodSafetyKorea response was not valid JSON. Check FOODSAFETYKOREA_API_KEY on the proxy server.",
        { code: "upstream_invalid_response" }
      );
    }

    const contentType = response.headers.get("content-type") || "unknown";
    throw new ProxyError(`Upstream response was not valid JSON (content-type: ${contentType}).`, {
      code: "upstream_invalid_response"
    });
  }
}

function extractDataGoItems(payload) {
  const raw = payload?.body?.items?.item;
  if (Array.isArray(raw)) {
    return raw.filter((item) => item && typeof item === "object");
  }
  if (raw && typeof raw === "object") {
    return [raw];
  }
  return [];
}

function extractFoodRecallRows(payload) {
  const raw = payload?.I0490?.row;
  if (Array.isArray(raw)) {
    return raw.filter((item) => item && typeof item === "object");
  }
  if (raw && typeof raw === "object") {
    return [raw];
  }
  return [];
}

function normalizeEasyDrugItem(item) {
  return {
    source: "drug_easy_info",
    item_name: summarizeText(item.itemName),
    company_name: summarizeText(item.entpName),
    efficacy: summarizeText(item.efcyQesitm),
    how_to_use: summarizeText(item.useMethodQesitm),
    warnings: summarizeText(item.atpnWarnQesitm),
    cautions: summarizeText(item.atpnQesitm),
    interactions: summarizeText(item.intrcQesitm),
    side_effects: summarizeText(item.seQesitm),
    storage: summarizeText(item.depositMethodQesitm),
    item_seq: summarizeText(item.itemSeq)
  };
}

function normalizeSafeStandbyDrugItem(item) {
  return {
    source: "safe_standby_medicine",
    item_name: summarizeText(item.PRDLST_NM),
    company_name: summarizeText(item.BSSH_NM),
    efficacy: summarizeText(item.EFCY_QESITM),
    how_to_use: summarizeText(item.USE_METHOD_QESITM),
    warnings: summarizeText(item.ATPN_WARN_QESITM),
    cautions: summarizeText(item.ATPN_QESITM),
    interactions: summarizeText(item.INTRC_QESITM),
    side_effects: summarizeText(item.SE_QESITM)
  };
}

function normalizeImproperFoodItem(item) {
  const reasonParts = [summarizeText(item.IMPROPT_ITM), summarizeText(item.INSPCT_RESULT)].filter(Boolean);

  return {
    source: "mfds_improper_food",
    product_name: summarizeText(item.PRDUCT),
    company_name: summarizeText(item.ENTRPS),
    reason: reasonParts.join("; "),
    created_at: summarizeText(item.REGIST_DT),
    category: summarizeText(item.FOOD_TY)
  };
}

function normalizeFoodRecallRow(item) {
  return {
    source: "foodsafetykorea_recall",
    product_name: summarizeText(item.PRDLST_NM || item.PRDTNM),
    company_name: summarizeText(item.BSSH_NM || item.BSSHNM),
    reason: summarizeText(item.RTRVLPRVNS),
    created_at: summarizeText(item.CRET_DTM),
    distribution_deadline: summarizeText(item.DISTBTMLMT),
    category: summarizeText(item.PRDLST_TYPE || item.PRDLST_CD_NM)
  };
}

function filterFoodSafetyItems(items, query) {
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return items;
  }

  const match = (value) => summarizeText(value).toLowerCase().includes(needle);
  const productMatches = items.filter((item) => match(item.product_name));
  if (productMatches.length > 0) {
    return productMatches;
  }

  const companyMatches = items.filter((item) => match(item.company_name));
  if (companyMatches.length > 0) {
    return companyMatches;
  }

  return items.filter((item) => match(item.reason));
}

async function fetchMfdsDrugLookup({ itemNames, limit, dataGoKrApiKey, fetchImpl = global.fetch }) {
  const items = [];

  for (const itemName of itemNames) {
    const [easyPayload, safePayload] = await Promise.all([
      requestJson(DRUG_EASY_ENDPOINT, {
        fetchImpl,
        params: {
          ServiceKey: dataGoKrApiKey,
          pageNo: 1,
          numOfRows: limit,
          type: "json",
          itemName
        }
      }),
      requestJson(SAFE_STAD_ENDPOINT, {
        fetchImpl,
        params: {
          serviceKey: dataGoKrApiKey,
          pageNo: 1,
          numOfRows: limit,
          type: "json",
          PRDLST_NM: itemName
        }
      })
    ]);

    items.push(...extractDataGoItems(easyPayload).map(normalizeEasyDrugItem));
    items.push(...extractDataGoItems(safePayload).map(normalizeSafeStandbyDrugItem));
  }

  return {
    query: {
      item_names: itemNames,
      limit
    },
    items,
    note: "상호작용 문구는 공식 품목 안내를 그대로 요약한 참고 정보이며, 복용 가능 여부의 최종 판단은 약사·의료진 확인이 필요합니다."
  };
}

async function fetchMfdsFoodSafetySearch({
  query,
  limit,
  dataGoKrApiKey,
  foodsafetyKoreaApiKey,
  fetchImpl = global.fetch
}) {
  const warnings = [];
  const items = [];

  if (dataGoKrApiKey) {
    try {
      const improperPayload = await requestJson(IMPROPER_FOOD_ENDPOINT, {
        fetchImpl,
        params: {
          ServiceKey: dataGoKrApiKey,
          pageNo: 1,
          numOfRows: Math.max(limit * 5, 50),
          type: "json"
        }
      });
      items.push(...extractDataGoItems(improperPayload).map(normalizeImproperFoodItem));
    } catch (error) {
      warnings.push(error.message);
    }
  } else {
    warnings.push("DATA_GO_KR_API_KEY is not configured on the proxy server, so improper-food live lookups were skipped.");
  }

  const recallUrl = foodsafetyKoreaApiKey
    ? FOOD_RECALL_LIVE_URL.replace("{apiKey}", encodeURIComponent(foodsafetyKoreaApiKey))
    : FOOD_RECALL_SAMPLE_URL;

  try {
    const recallPayload = await requestJson(
      recallUrl
        .replace("{start}", "1")
        .replace("{end}", String(Math.max(limit * 5, 50))),
      { fetchImpl }
    );
    items.push(...extractFoodRecallRows(recallPayload).map(normalizeFoodRecallRow));
    if (!foodsafetyKoreaApiKey) {
      warnings.push("FOODSAFETYKOREA_API_KEY is not configured on the proxy server, so recall results use the public sample feed.");
    }
  } catch (error) {
    warnings.push(error.message);
  }

  return {
    query,
    items: filterFoodSafetyItems(items, query).slice(0, limit),
    warnings,
    note: "이 결과는 공식 회수·부적합 공개 목록 기반 참고 정보이며, 섭취 가능 여부의 최종 판단은 증상 인터뷰와 의료진 상담이 우선입니다."
  };
}

module.exports = {
  fetchMfdsDrugLookup,
  fetchMfdsFoodSafetySearch,
  normalizeMfdsDrugLookupQuery,
  normalizeMfdsFoodSafetyQuery
};
