import test from 'node:test';
import assert from 'node:assert/strict';
import { localizedCartUrl, updateCartLinkLanguages } from '../src/chat/cart-links.ts';

test('RU to KZ language switch updates the existing saved-cart href without replacing its read token', () => {
  const original = 'http://localhost:8000/cart/read-capability?language=ru&view=cart#items';
  const result = new URL(localizedCartUrl(original, 'kz'));
  assert.equal(result.searchParams.get('language'), 'kk');
  assert.equal(result.pathname, '/cart/read-capability');
  assert.equal(result.searchParams.get('view'), 'cart');
  assert.equal(result.hash, '#items');
  assert.equal(new URL(localizedCartUrl(result.href, 'en')).searchParams.get('language'), 'en');
  assert.equal(new URL(localizedCartUrl(result.href, 'ru')).searchParams.get('language'), 'ru');
});
test('old and new confirmation links follow the selected language while historical text and offers remain untouched', () => {
  const pending = { offer_token: 'pending-capability', product_id: 1, quantity: 5, price: 12, expires_in_seconds: 600 };
  const originalOffer = JSON.stringify(pending);
  const links = [
    { href: 'http://localhost:8000/cart/old-read-token?language=ru', textContent: 'Открыть корзину', pending },
    { href: 'https://demo.example/nexis/cart/new-read-token', textContent: 'Open saved cart' },
    { href: 'https://ekt.kz/personal/cart/', textContent: 'Корзина ekt.kz' },
  ];
  const text = links.map((link) => link.textContent);
  updateCartLinkLanguages(links, 'kz');
  assert.equal(new URL(links[0].href).searchParams.get('language'), 'kk');
  assert.equal(new URL(links[1].href).searchParams.get('language'), 'kk');
  assert.equal(links[2].href, 'https://ekt.kz/personal/cart/');
  assert.deepEqual(links.map((link) => link.textContent), text);
  assert.equal(JSON.stringify(pending), originalOffer);
});
test('cart localization preserves catalog and document URLs and rejects unsafe URLs', () => {
  for (const url of ['https://ekt.kz/catalog/product/?language=ru', 'https://ekt.kz/document.pdf', 'https://ekt.kz/personal/cart/']) {
    assert.equal(localizedCartUrl(url, 'en'), url);
  }
  for (const url of [null, '', 'javascript:alert(1)', 'https://user:password@example.com/cart/token']) {
    assert.equal(localizedCartUrl(url, 'en'), null);
  }
});
