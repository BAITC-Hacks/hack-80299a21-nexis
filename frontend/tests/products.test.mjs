import test from 'node:test';
import assert from 'node:assert/strict';
import { normaliseProduct, canOffer, nullableNumber, productUrl, offeredQuantity } from '../src/chat/products.ts';

test('structured specifications become readable name/value strings', () => {
  const result = normaliseProduct({ id: 1, specifications: [{ name: 'Ток', value: '16 А' }, { name: 'Полюса', value: 3 }, { name: 'Серия', value: ['A', 'B'] }] });
  assert.deepEqual(result.specifications, ['Ток: 16 А', 'Полюса: 3', 'Серия: A, B']);
  assert.ok(result.specifications.every((s) => !s.includes('[object Object]')));
});
test('unknown price/stock remain null and cannot authorize an offer', () => {
  const product = normaliseProduct({ id: 1, price: null, quantity: null });
  assert.equal(product.price, null); assert.equal(product.stock, null); assert.equal(canOffer(product), false);
});
test('unverified values are distinct from verified zero stock', () => {
  const unverified = normaliseProduct({ id: 1, price: 20, quantity: 5 });
  const zero = normaliseProduct({ id: 1, price: 20, quantity: 0, price_verified: true, stock_verified: true });
  assert.equal(unverified.stockVerified, false); assert.equal(canOffer(unverified), false);
  assert.equal(zero.stock, 0); assert.equal(zero.stockVerified, true); assert.equal(canOffer(zero), false);
});
test('verified positive values allow an offer within minimum quantity', () => {
  assert.equal(canOffer(normaliseProduct({ id: 1, price: 20, quantity: 5, price_verified: true, stock_verified: true })), true);
  assert.equal(canOffer(normaliseProduct({ id: 1, price: 20, quantity: 5, price_verified: true, stock_verified: true, min_order_quantity: 10 })), false);
});
test('product IDs and names are never generated or replaced by fixtures', () => {
  assert.equal(normaliseProduct({ name: 'no ID' }), null);
  assert.equal(normaliseProduct({ id: -1 }), null);
  const product = normaliseProduct({ id: 515291, name: 'Реальное имя из API' });
  assert.equal(product.name, 'Реальное имя из API');
});
test('warnings, date and warehouse unknown values are retained', () => {
  const result = normaliseProduct({ id: 1, data_quality_warnings: ['Несовпадение тока'], last_checked_at: '2026-09-23T10:00:00Z', stores: [{ name: 'Алматы', quantity: null }] });
  assert.deepEqual(result.warnings, ['Несовпадение тока']);
  assert.equal(result.checkedAt, '2026-09-23T10:00:00Z'); assert.equal(result.stores[0].quantity, null);
});
test('unsafe certificate/image URLs are rejected', () => {
  assert.equal(productUrl('javascript:alert(1)'), null); assert.equal(productUrl('https://user:password@host/path'), null);
  assert.equal(productUrl('https://ekt.kz/cert.pdf'), 'https://ekt.kz/cert.pdf');
});
test('invalid numeric facts are never coerced to real stock or price', () => {
  for (const value of [null, undefined, '', '23', false, -1, NaN, Infinity]) assert.equal(nullableNumber(value), null);
  assert.equal(nullableNumber(0), 0);
});
test('matching card starts with the exact pending-offer quantity', () => {
  const product = normaliseProduct({ id: 42 });
  assert.equal(offeredQuantity(product, { product_id: 42, quantity: 2 }), 2);
  assert.equal(offeredQuantity(product, { product_id: 43, quantity: 2 }), undefined);
  assert.equal(offeredQuantity(product, null), undefined);
  assert.equal(offeredQuantity(product, { product_id: 42, quantity: 0 }), undefined);
  assert.equal(offeredQuantity(product, { product_id: 42, quantity: 1.5 }), undefined);
});

test('stable specification keys translate labels without altering names, values or identifiers', () => {
  for (const [language, expected] of [['ru', 'Номинальный ток'], ['kz', 'Номиналды ток'], ['en', 'Rated current']]) {
    const source = { id: 515291, name: '027228 АВ DRX250 MT Legrand', article: '200300285_', specifications: [
      { key: 'NOMINALNYY_TOK', name: 'Номинальный ток', value: '160 A' },
      { key: 'unknown_key', name: 'Original source label', value: '027228' },
    ] };
    const product = normaliseProduct(source, language);
    assert.equal(product.name, source.name);
    assert.equal(product.article, source.article);
    assert.deepEqual(product.specifications, [`${expected}: 160 A`, 'Original source label: 027228']);
    assert.deepEqual(product.specificationEntries, source.specifications);
  }
});
