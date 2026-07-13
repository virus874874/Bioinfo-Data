import unittest

from gdc_scout.core import Scout


class ParserTests(unittest.TestCase):
    def test_stage_and_endpoint(self):
        case = {"diagnoses": [{"ajcc_pathologic_stage": "Stage II", "days_to_death": 400}]}
        self.assertTrue(Scout._has_stage(case))
        self.assertTrue(Scout._has_endpoint(case))

    def test_unknown_stage_is_not_present(self):
        self.assertFalse(Scout._has_stage({"diagnoses": [{"ajcc_pathologic_stage": "Not Reported"}]}))

    def test_file_access_summary(self):
        body = {"data": {"pagination": {"total": 9}, "aggregations": {"access": {"buckets": [{"key": "public", "doc_count": 8}, {"key": "controlled", "doc_count": 1}]}}}}
        self.assertEqual(Scout._file_summary(body), ("mixed", 9))


if __name__ == "__main__": unittest.main()

