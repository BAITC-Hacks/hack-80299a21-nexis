from backend.tests.support import APIHarness
from spec_parser import SpecificationParser


class SpecificationDelimiterTests(APIHarness):
    def upload(self, text):
        return self.client.post("/api/agent/upload-spec", files={"file": ("specification.txt", text.encode("utf-8"), "text/plain")})

    def test_semicolon_header_quantity_and_unknown_row(self):
        self.transport.products[1001]["article"] = "200300285_"
        text = "Артикул;Количество\n200300285_;2\nНЕСУЩЕСТВУЮЩИЙ-XYZ-900;3\n"
        response = self.upload(text)
        self.assertEqual(response.status_code, 200, response.text)
        estimate = response.json()["estimate"]
        self.assertEqual(len(estimate["matched_items"]), 1)
        self.assertEqual(estimate["matched_items"][0]["quantity"], 2)
        self.assertEqual(estimate["total_estimate_kzt"], 2000)
        self.assertEqual(estimate["ignored_lines"], ["Артикул;Количество"])
        self.assertEqual(len(estimate["unmatched_items"]), 1)
        self.assertEqual(estimate["unmatched_items"][0]["query"], "НЕСУЩЕСТВУЮЩИЙ-XYZ-900")
        self.assertEqual(estimate["unmatched_items"][0]["quantity"], 3)
        self.assertFalse(estimate["estimate_complete"])
        self.assertEqual(self.cart()["total_items"], 0)

    def test_tab_header_with_reordered_columns(self):
        response = self.upload("Количество\tАртикул\tЦена\n3\tTEST-1001\t999999")
        estimate = response.json()["estimate"]
        self.assertEqual(estimate["matched_items"][0]["quantity"], 3)
        self.assertEqual(estimate["total_estimate_kzt"], 3000)
        self.assertTrue(estimate["estimate_complete"])

    def test_quoted_cells_and_embedded_semicolon(self):
        rows, ignored = SpecificationParser.rows('"Артикул";"Наименование";"Количество"\n"TEST-1001";"Автомат; выключатель";"2"')
        self.assertEqual(len(ignored), 1)
        self.assertEqual(rows[0]["query"], "TEST-1001 Автомат; выключатель")
        self.assertEqual(rows[0]["quantity"], 2)

    def test_invalid_quantities_remain_unknown_instead_of_becoming_one(self):
        for value in ("", "0", "-2", "+2", "1.5", "1,5", "2e1", "NaN", "100001", "2 штуки"):
            rows, _ = SpecificationParser.rows("Артикул;Количество\nTEST-1001;" + value)
            self.assertIsNone(rows[0]["quantity"], value)
            self.assertTrue(rows[0]["quantity_warning"])
        for value in ("2", "2.0", "2,00"):
            rows, _ = SpecificationParser.rows("Артикул;Количество\nTEST-1001;" + value)
            self.assertEqual(rows[0]["quantity"], 2, value)

    def test_number_inside_article_is_never_quantity(self):
        for text in ("TEST-1001", "200300285_", "TEST-1001 2", "TEST-1001;2"):
            rows, _ = SpecificationParser.rows(text)
            self.assertIsNone(rows[0]["quantity"], text)
            self.assertEqual(rows[0]["query"], text)

    def test_delimiter_switch_requires_a_new_header(self):
        rows, _ = SpecificationParser.rows("Количество;Артикул\n2;TEST-1001\nTEST-1001\nTEST-1001\t3")
        self.assertEqual(rows[0]["quantity"], 2)
        self.assertEqual(rows[1]["query"], "TEST-1001")
        self.assertIsNone(rows[1]["quantity"])
        self.assertIsNone(rows[2]["quantity"])
