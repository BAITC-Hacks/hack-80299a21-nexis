import copy

from backend.tests.support import APIHarness, product
from ekt_client import EktClient, rating


class CatalogTests(APIHarness):
    def test_electrical_units_and_ambiguous_voltage(self):
        target = self.catalog.get_product_detail(1002)
        raw = product()
        raw["properties"]["NOMINALNAYA_OTKLYUCHAYUSHCHAYA_SPOSOBNOST"] = "6000 А"
        self.assertTrue(EktClient.analog_match(target, EktClient._normalise_detail(raw)))
        raw["properties"]["NOMINALNAYA_OTKLYUCHAYUSHCHAYA_SPOSOBNOST"] = "1000 А"
        self.assertFalse(EktClient.analog_match(target, EktClient._normalise_detail(raw)))
        raw["properties"]["NOMINALNOE_NAPRYAZHENIE"] = "230/400В"
        self.assertIsNone(EktClient._normalise_detail(raw)["technical"]["voltage"])
        self.assertEqual(rating("0.03 A", "leakage"), 30)
        self.assertEqual(rating("0.4 кВ", "voltage"), 400)

    def test_detail_ttl_and_forced_refresh(self):
        first = self.catalog.get_product_detail(1001)
        self.transport.products[1001]["price"] = 2000
        self.assertEqual(self.catalog.get_product_detail(1001)["price"], 1000)
        self.clock.now += self.catalog.detail_ttl + 1
        fresh = self.catalog.get_product_detail(1001)
        self.assertEqual(fresh["price"], 2000)
        self.assertNotEqual(first["last_checked_at"], fresh["last_checked_at"])
        self.transport.fail = True
        self.assertIsNone(self.catalog.get_product_detail(1001, force_refresh=True))
        self.clock.now += self.catalog.detail_ttl + 1
        self.assertIsNone(self.catalog.get_product_detail(1001))

    def test_page_ttl_and_exact_article_in_sentence(self):
        found = self.catalog.search_products("Нужен TEST-1001 2 шт.")
        self.assertEqual(found[0]["_match_type"], "exact")
        self.transport.products[1001]["name"] = "Новое имя"
        self.clock.now += self.catalog.catalog_ttl + 1
        self.assertEqual(self.catalog.search_products("TEST-1001")[0]["name"], "Новое имя")
        self.assertEqual(self.catalog.search_products("неизвестныймарсианскийтовар"), [])

    def test_missing_and_invalid_values_stay_unknown(self):
        for value in (None, "NaN", "Infinity", -3, True, "invalid"):
            normalized = EktClient._normalise_detail(product(price=value, quantity=value))
            self.assertIsNone(normalized["quantity"])
            self.assertIsNone(normalized["price"])
            self.assertFalse(normalized["stock_verified"])
            self.assertFalse(normalized["price_verified"])
        zero = EktClient._normalise_detail(product(quantity=0))
        self.assertEqual(zero["quantity"], 0)
        self.assertTrue(zero["stock_verified"])

    def test_details_are_not_mutated_through_response_objects(self):
        detail = self.catalog.get_product_detail(1001)
        detail["quantity"] = 999999
        detail["properties"]["NOMINALNYY_TOK"] = "bad"
        self.assertEqual(self.catalog.get_product_detail(1001)["quantity"], 5)
        self.assertEqual(self.catalog.get_product_detail(1001)["properties"]["NOMINALNYY_TOK"], "16 А")

    def test_analog_must_match_voltage_current_poles_and_capacity(self):
        target = self.catalog.get_product_detail(1002)
        analogs = self.catalog.find_analogs(target)
        self.assertEqual([item["id"] for item in analogs], [1001])
        for field in ("NOMINALNOE_NAPRYAZHENIE", "KOLICHESTVO_POLYUSOV", "NOMINALNAYA_OTKLYUCHAYUSHCHAYA_SPOSOBNOST"):
            raw = copy.deepcopy(self.transport.products[1001])
            raw["properties"][field] = "1"
            candidate = EktClient._normalise_detail(raw)
            self.assertEqual(EktClient.analog_match(target, candidate), [], field)

    def test_conflicting_current_blocks_automatic_analog(self):
        raw = product()
        raw["properties"]["NOMINALNYY_TOK"] = "250 А"
        bad = EktClient._normalise_detail(raw)
        self.assertTrue(bad["data_quality_warnings"])
        self.assertEqual(self.catalog.find_analogs(bad), [])

    def test_missing_critical_voltage_blocks_substitution(self):
        raw = product()
        raw["name"] = "Автомат 16А 3P"
        raw["properties"].pop("NOMINALNOE_NAPRYAZHENIE")
        candidate = EktClient._normalise_detail(raw)
        self.assertEqual(EktClient.analog_match(self.catalog.get_product_detail(1002), candidate), [])
