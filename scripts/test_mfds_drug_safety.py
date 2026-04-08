import unittest

from scripts.mfds_drug_safety import (
    build_drug_interview,
    normalize_easy_drug_item,
    normalize_safe_stad_item,
    resolve_service_key,
)


class DrugInterviewTest(unittest.TestCase):
    def test_build_drug_interview_requires_followup_questions_and_red_flags(self):
        interview = build_drug_interview(
            question="타이레놀이랑 판콜 같이 먹어도 되나요?",
            symptoms="두드러기와 어지러움",
        )

        self.assertEqual(interview["domain"], "drug")
        self.assertIn("누가 복용하려는지", interview["must_ask"][0])
        self.assertTrue(any("얼마나" in item for item in interview["must_ask"]))
        self.assertTrue(any("복용 중인 약" in item for item in interview["must_ask"]))
        self.assertTrue(any("알레르기" in item for item in interview["must_ask"]))
        self.assertTrue(any("호흡곤란" in item for item in interview["red_flags"]))
        self.assertTrue(any("의식" in item for item in interview["red_flags"]))
        self.assertIn("즉시 119", interview["urgent_action"])


class DrugNormalizationTest(unittest.TestCase):
    def test_normalize_easy_drug_item_extracts_public_safety_summary(self):
        item = normalize_easy_drug_item(
            {
                "itemName": "타이레놀정160밀리그램",
                "entpName": "한국얀센",
                "efcyQesitm": "감기로 인한 발열 및 동통에 사용합니다.",
                "useMethodQesitm": "만 12세 이상은 필요시 복용합니다.",
                "atpnWarnQesitm": "매일 세 잔 이상 술을 마시는 사람은 전문가와 상의하십시오.",
                "atpnQesitm": "간질환 환자는 주의하십시오.",
                "intrcQesitm": "다른 해열진통제와 함께 복용하지 마십시오.",
                "seQesitm": "발진, 구역이 나타날 수 있습니다.",
                "depositMethodQesitm": "실온 보관하십시오.",
            }
        )

        self.assertEqual(item["source"], "drug_easy_info")
        self.assertEqual(item["item_name"], "타이레놀정160밀리그램")
        self.assertEqual(item["company_name"], "한국얀센")
        self.assertIn("발열", item["efficacy"])
        self.assertIn("해열진통제", item["interactions"])
        self.assertIn("실온", item["storage"])

    def test_normalize_safe_stad_item_extracts_store_medicine_fields(self):
        item = normalize_safe_stad_item(
            {
                "PRDLST_NM": "어린이타이레놀현탁액",
                "BSSH_NM": "한국존슨앤드존슨판매(유)",
                "EFCY_QESITM": "해열 및 진통",
                "USE_METHOD_QESITM": "용법에 따라 복용",
                "ATPN_WARN_QESITM": "과량복용 주의",
                "INTRC_QESITM": "다른 아세트아미노펜 제제와 병용 주의",
                "SE_QESITM": "드물게 발진",
            }
        )

        self.assertEqual(item["source"], "safe_standby_medicine")
        self.assertEqual(item["item_name"], "어린이타이레놀현탁액")
        self.assertIn("아세트아미노펜", item["interactions"])


class ServiceKeyResolutionTest(unittest.TestCase):
    def test_resolve_service_key_requires_data_go_kr_api_key(self):
        with self.assertRaisesRegex(ValueError, "DATA_GO_KR_API_KEY"):
            resolve_service_key(None, env={})

        self.assertEqual(resolve_service_key("abc", env={}), "abc")
        self.assertEqual(resolve_service_key(None, env={"DATA_GO_KR_API_KEY": "xyz"}), "xyz")


if __name__ == "__main__":
    unittest.main()
