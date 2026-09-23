from concurrent.futures import ThreadPoolExecutor

from backend.tests.support import APIHarness


class CartChangesTests(APIHarness):
    def setUp(self):
        super().setUp()
        self.assertEqual(self.confirm(self.offer(quantity=2).json()).status_code, 200)

    def change_offer(self, quantity):
        return self.client.post('/api/cart/change-offer', headers=self.headers,
                                json={'product_id': 1001, 'quantity': quantity})

    def change(self, offer, **extra):
        return self.client.post('/api/cart/change', headers=self.headers, json={
            'product_id': offer['product_id'], 'quantity': offer['quantity'],
            'offer_token': offer['offer_token'], 'confirmed': True, **extra})

    def test_preview_never_mutates_and_requires_confirmation(self):
        offer = self.change_offer(3).json()
        self.assertEqual(offer['previous_quantity'], 2)
        self.assertEqual(self.cart()['total_items'], 2)
        self.assertEqual(self.change(offer, confirmed=False).status_code, 409)
        self.assertEqual(self.cart()['total_items'], 2)
        response = self.change(offer)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['cart_confirmation']['quantity'], 3)
        self.assertEqual(self.cart()['total_items'], 3)

    def test_decrease_and_remove_require_individual_offers(self):
        self.assertEqual(self.change(self.change_offer(1).json()).status_code, 200)
        removal = self.change_offer(0).json()
        self.assertEqual(self.cart()['total_items'], 1)
        result = self.change(removal)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['cart'], [])
        self.assertEqual(self.change(removal).status_code, 409)

    def test_removal_is_available_when_catalog_is_down(self):
        self.transport.fail = True
        offer = self.change_offer(0)
        self.assertEqual(offer.status_code, 200)
        self.assertIsNone(offer.json()['stock_available'])
        self.assertEqual(self.change(offer.json()).status_code, 200)

    def test_price_and_stock_are_rechecked(self):
        offer = self.change_offer(4).json()
        self.transport.products[1001]['quantity'] = 3
        self.assertEqual(self.change(offer).json()['code'], 'insufficient_stock')
        self.transport.products[1001]['quantity'] = 5
        self.transport.products[1001]['price'] = 2000
        self.assertEqual(self.change(offer).json()['code'], 'price_changed')
        self.assertEqual(self.cart()['total_items'], 2)

    def test_add_and_change_tokens_are_not_interchangeable(self):
        offer = self.change_offer(3).json()
        self.assertEqual(self.confirm(offer).status_code, 409)
        add_offer = self.offer().json()
        self.assertEqual(self.change(add_offer).status_code, 409)
        self.assertEqual(self.cart()['total_items'], 2)

    def test_wrong_quantity_session_and_expiry(self):
        offer = self.change_offer(3).json()
        self.assertEqual(self.change(offer, quantity=1).status_code, 409)
        original_headers = self.headers
        self.headers = {'X-Session-Id': self.client.post('/api/session').json()['session_id']}
        self.assertEqual(self.change(offer).status_code, 409)
        self.headers = original_headers
        self.clock.now += offer['expires_in_seconds'] + 1
        self.assertEqual(self.change(offer).status_code, 409)
        self.assertEqual(self.cart()['total_items'], 2)

    def test_no_stale_write_after_parallel_confirmation(self):
        offer = self.change_offer(3).json()
        with ThreadPoolExecutor(max_workers=5) as pool:
            statuses = list(pool.map(lambda _: self.change(offer).status_code, range(5)))
        self.assertEqual(statuses.count(200), 1)
        self.assertEqual(statuses.count(409), 4)
        self.assertEqual(self.cart()['total_items'], 3)

    def test_validation_missing_item_and_noop(self):
        for invalid in (-1, 1.5, True, '3', 100001):
            self.assertEqual(self.change_offer(invalid).status_code, 422)
        self.assertEqual(self.change_offer(2).json()['code'], 'quantity_unchanged')
        self.change(self.change_offer(0).json())
        self.assertEqual(self.change_offer(0).status_code, 404)

    def test_api_failure_does_not_authorize_increase(self):
        offer = self.change_offer(3).json()
        self.transport.fail = True
        self.assertEqual(self.change(offer).status_code, 503)
        self.assertEqual(self.cart()['total_items'], 2)

    def test_changed_cart_requires_new_confirmation(self):
        offer = self.change_offer(3).json()
        # Simulate another writer while keeping the original proposal for validation.
        key = self.carts.session(self.sid)
        with self.carts.db() as db:
            db.execute("DELETE FROM cart_items WHERE session=?", (key,))
        self.assertEqual(self.change(offer).json()['code'], 'cart_changed')
