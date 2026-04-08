import unittest
from unittest import mock

from scripts.mfds_food_safety import (
    ApiError,
    FOOD_RECALL_LIVE_URL,
    FOOD_RECALL_SAMPLE_URL,
    _request_json,
    build_food_interview,
    filter_food_items,
    normalize_food_recall_row,
    normalize_improper_food_item,
    resolve_data_go_service_key,
)


class FoodInterviewTest(unittest.TestCase):
    def test_build_food_interview_requires_symptom_followup_and_red_flags(self):
        interview = build_food_interview(
            question="이 김밥 먹어도 되나요?",
            symptoms="복통과 설사",
        )

        self.assertEqual(interview["domain"], "food")
        self.assertTrue(any("언제" in item for item in interview["must_ask"]))
        self.assertTrue(any("얼마나" in item for item in interview["must_ask"]))
        self.assertTrue(any("기저질환" in item for item in interview["must_ask"]))
        self.assertTrue(any("알레르기" in item for item in interview["must_ask"]))
        self.assertTrue(any("혈변" in item for item in interview["red_flags"]))
        self.assertTrue(any("탈수" in item for item in interview["red_flags"]))
        self.assertIn("응급실", interview["urgent_action"])


class FoodNormalizationTest(unittest.TestCase):
    def test_normalize_food_recall_row_keeps_official_recall_fields(self):
        item = normalize_food_recall_row(
            {
                "PRDLST_NM": "맛있는김밥",
                "BSSH_NM": "예시식품",
                "RTRVLPRVNS": "대장균 기준 규격 부적합",
                "CRET_DTM": "2026-04-07 18:03:56.058442",
                "DISTBTMLMT": "2027-12-18",
                "PRDLST_TYPE": "가공식품",
            }
        )

        self.assertEqual(item["source"], "foodsafetykorea_recall")
        self.assertEqual(item["product_name"], "맛있는김밥")
        self.assertEqual(item["company_name"], "예시식품")
        self.assertIn("대장균", item["reason"])
        self.assertEqual(item["category"], "가공식품")

    def test_normalize_improper_food_item_keeps_official_improper_food_fields(self):
        item = normalize_improper_food_item(
            {
                "PRDUCT": "예시 유부초밥",
                "ENTRPS": "예시푸드",
                "IMPROPT_ITM": "황색포도상구균",
                "INSPCT_RESULT": "기준 부적합",
                "FOOD_TY": "즉석조리식품",
                "REGIST_DT": "2026-04-08",
            }
        )

        self.assertEqual(item["source"], "mfds_improper_food")
        self.assertEqual(item["product_name"], "예시 유부초밥")
        self.assertEqual(item["company_name"], "예시푸드")
        self.assertIn("황색포도상구균", item["reason"])

    def test_filter_food_items_matches_product_and_company_names(self):
        items = [
            {"product_name": "맛있는김밥", "company_name": "예시식품"},
            {"product_name": "사과주스", "company_name": "김밥나라"},
        ]

        by_product = filter_food_items(items, "김밥")
        by_company = filter_food_items(items, "나라")

        self.assertEqual(len(by_product), 1)
        self.assertEqual(by_product[0]["product_name"], "맛있는김밥")
        self.assertEqual(len(by_company), 1)
        self.assertEqual(by_company[0]["company_name"], "김밥나라")


class FoodServiceKeyResolutionTest(unittest.TestCase):
    def test_resolve_data_go_service_key_requires_data_go_kr_api_key(self):
        with self.assertRaisesRegex(ValueError, "DATA_GO_KR_API_KEY"):
            resolve_data_go_service_key(None, env={})

        self.assertEqual(resolve_data_go_service_key("abc", env={}), "abc")
        self.assertEqual(resolve_data_go_service_key(None, env={"DATA_GO_KR_API_KEY": "xyz"}), "xyz")


class FoodRecallTransportTest(unittest.TestCase):
    def test_food_recall_urls_use_https(self):
        self.assertTrue(FOOD_RECALL_SAMPLE_URL.startswith("https://"))
        self.assertTrue(FOOD_RECALL_LIVE_URL.startswith("https://"))

    def test_request_json_turns_invalid_foodsafety_key_html_into_api_error(self):
        class FakeResponse:
            headers = {"Content-Type": "text/html;charset=utf-8"}

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return "<html><script>alert('invalid key');</script></html>".encode("utf-8")

        url = FOOD_RECALL_LIVE_URL.format(api_key="invalid-demo-key", start=1, end=1)

        with mock.patch("scripts.mfds_food_safety.urllib.request.urlopen", return_value=FakeResponse()):
            with self.assertRaisesRegex(ApiError, "foodsafetykorea-key"):
                _request_json(url)


if __name__ == "__main__":
    unittest.main()
