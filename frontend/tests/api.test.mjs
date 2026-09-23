import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiClient, ApiError, apiLanguage } from '../src/chat/api.ts';

const json = (value, status = 200, headers = {}) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json', ...headers } });
const memory = () => {
  const entries = new Map();
  return { getItem: (k) => entries.get(k) || null, setItem: (k, v) => entries.set(k, v), removeItem: (k) => entries.delete(k) };
};

test('KZ maps to kk; English and Russian use their own consultation languages', () => {
  assert.equal(apiLanguage('kz'), 'kk');
  assert.equal(apiLanguage('ru'), 'ru');
  assert.equal(apiLanguage('en'), 'en');
});
test('native fetch is called without an ApiClient receiver', async () => {
  const api = new ApiClient('/api', async function (url) {
    assert.equal(this, undefined, 'Browser fetch must not be called as an ApiClient method');
    return url.endsWith('/session') ? json({ session_id: 'one' }) : json({ items: [] });
  });
  assert.deepEqual(await api.request('/cart'), { items: [] });
});
test('concurrent requests create one server session and share its header', async () => {
  const calls = [];
  const api = new ApiClient('/api', async (url, options) => {
    calls.push({ url, options });
    return url.endsWith('/session') ? json({ session_id: 'session-one' }) : json({ items: [] });
  }, memory());
  await Promise.all([api.request('/cart'), api.request('/cart')]);
  assert.equal(calls.filter((c) => c.url.endsWith('/session')).length, 1);
  assert.equal(calls[1].options.headers.get('X-Session-Id'), 'session-one');
  assert.equal(calls[2].options.headers.get('X-Session-Id'), 'session-one');
});
test('session persists and tokens never appear in request URLs', async () => {
  const storage = memory();
  const urls = [];
  const fetcher = async (url) => { urls.push(url); return url.endsWith('/session') ? json({ session_id: 'private-token' }) : json({}); };
  await new ApiClient('/api', fetcher, storage).request('/cart');
  await new ApiClient('/api', fetcher, storage).request('/cart');
  assert.equal(urls.filter((u) => u.endsWith('/session')).length, 1);
  assert.ok(urls.every((u) => !u.includes('private-token')));
});
test('expired read obtains new session and retries exactly once', async () => {
  let sessions = 0, reads = 0, resets = 0;
  const api = new ApiClient('/api', async (url) => {
    if (url.endsWith('/session')) return json({ session_id: 'token-' + ++sessions });
    return ++reads === 1 ? json({ detail: 'expired' }, 401) : json({ items: [1] });
  });
  api.onSessionReset = () => resets++;
  assert.deepEqual(await api.request('/cart'), { items: [1] });
  assert.equal(sessions, 2); assert.equal(reads, 2); assert.equal(resets, 1);
});
test('expired confirmed cart write is NOT replayed', async () => {
  let sessions = 0, writes = 0;
  const api = new ApiClient('/api', async (url) => {
    if (url.endsWith('/session')) return json({ session_id: 'token-' + ++sessions });
    writes++; return json({ detail: 'expired' }, 401);
  });
  await assert.rejects(api.post('/cart/add', { product_id: 3, confirmed: true, offer_token: 'once' }), (e) => e.code === 'session_expired');
  assert.equal(writes, 1); assert.equal(sessions, 2);
});
test('chat confirmation is also treated as a write and never replayed on 401', async () => {
  let calls = 0;
  const api = new ApiClient('/api', async (url) => {
    if (url.endsWith('/session')) return json({ session_id: 'token' + calls });
    calls++; return json({}, 401);
  });
  await assert.rejects(api.post('/agent/chat', { message: 'Да, добавь' }), ApiError);
  assert.equal(calls, 1);
});
test('unavailable API returns actionable error without a synthetic response', async () => {
  const api = new ApiClient('/api', async () => { throw new TypeError('offline'); });
  await assert.rejects(api.request('/cart'), (e) => e instanceof ApiError && e.code === 'network_error');
});
test('server conflict message and stable code are preserved', async () => {
  const api = new ApiClient('/api', async (url) => url.endsWith('/session') ? json({ session_id: 'one' }) : json({ detail: 'Цена изменилась', code: 'price_changed' }, 409));
  await assert.rejects(api.post('/cart/add', {}), (e) => e.status === 409 && e.message === 'Цена изменилась' && e.code === 'price_changed');
});
test('429 respects Retry-After and is not automatically replayed', async () => {
  const api = new ApiClient('/api', async (url) => url.endsWith('/session') ? json({ session_id: 'one' }) : json({}, 429, { 'Retry-After': '12' }));
  await assert.rejects(api.request('/cart'), (e) => e.status === 429 && e.message.includes('12'));
});
test('multipart body is sent intact and browser sets Content-Type boundary', async () => {
  const body = new FormData(); body.append('file', new File(['a'], 'items.txt'));
  const api = new ApiClient('/api', async (url, options) => {
    if (url.endsWith('/session')) return json({ session_id: 'one' });
    assert.equal(options.body, body);
    assert.equal(options.headers.get('Content-Type'), null);
    assert.equal(options.headers.get('X-Session-Id'), 'one');
    return json({ estimate: {} });
  });
  await api.request('/agent/upload-spec', { method: 'POST', body });
});
test('private browsing storage failures keep session in memory', async () => {
  let creates = 0;
  const storage = { getItem() { throw Error(); }, setItem() { throw Error(); }, removeItem() { throw Error(); } };
  const api = new ApiClient('/api', async (url) => url.endsWith('/session') ? (creates++, json({ session_id: 'one' })) : json({}), storage);
  await api.request('/cart'); await api.request('/cart');
  assert.equal(creates, 1);
});

test('all API requests carry the canonical language including sessions and uploads', async () => {
  for (const [language, expected] of [['ru', 'ru'], ['kz', 'kk'], ['en', 'en']]) {
    const seen = [];
    const api = new ApiClient('/api', async (url, options) => {
      seen.push(url);
      assert.equal(options.headers.get('X-Language'), expected, url);
      return url.endsWith('/session') ? json({ session_id: 'one' }) : json({});
    });
    api.setLanguage(language);
    await api.request('/faq?q=delivery');
    await api.request('/cart');
    await api.post('/cart/offer', { product_id: 1, quantity: 2 });
    await api.post('/cart/add', { product_id: 1, quantity: 2, confirmed: true, offer_token: 'token' });
    await api.post('/cart/change-offer', { product_id: 1, quantity: 3 });
    await api.post('/cart/change', { product_id: 1, quantity: 3, confirmed: true, offer_token: 'change' });
    await api.post('/agent/chat', { language: apiLanguage(language), message: '515291' });
    await api.request('/agent/upload-spec', { method: 'POST', body: new FormData() });
    assert.equal(seen.length, 9);
  }
});
test('language switching keeps the same session and does not issue any requests on its own', async () => {
  const calls = [];
  const api = new ApiClient('/api', async (url, options) => {
    calls.push({ url, language: options.headers.get('X-Language'), session: options.headers.get('X-Session-Id') });
    return url.endsWith('/session') ? json({ session_id: 'keep-me' }) : json({});
  });
  await api.request('/cart');
  api.setLanguage('en');
  assert.equal(calls.length, 2);
  await api.request('/faq');
  api.setLanguage('kz');
  await api.request('/cart');
  assert.deepEqual(calls.slice(1).map((call) => call.session), ['keep-me', 'keep-me', 'keep-me']);
  assert.deepEqual(calls.slice(1).map((call) => call.language), ['ru', 'en', 'kk']);
});
test('legacy Russian backend errors are translated for EN and KK by stable code', async () => {
  for (const [language, expected] of [['en', /price changed/i], ['kz', /Баға өзгерді/]]) {
    const api = new ApiClient('/api', async (url) => url.endsWith('/session') ? json({ session_id: 'one' }) : json({ detail: 'Цена изменилась', code: 'price_changed' }, 409));
    api.setLanguage(language);
    await assert.rejects(api.post('/cart/add', {}), (error) => expected.test(error.message) && error.code === 'price_changed');
  }
});
test('v3 localized error detail and params are retained', async () => {
  const api = new ApiClient('/api', async (url) => url.endsWith('/session') ? json({ session_id: 'one' }) : json({ detail: 'Only 3 available.', code: 'insufficient_stock', params: { remaining: 3 }, answer_language: 'en' }, 409));
  api.setLanguage('en');
  await assert.rejects(api.post('/cart/add', {}), (error) => error.message === 'Only 3 available.' && error.params.remaining === 3);
});
test('unknown foreign-language errors use a local generic error without internal details', async () => {
  const api = new ApiClient('/api', async (url) => url.endsWith('/session') ? json({ session_id: 'one' }) : json({ detail: 'Внутренняя ошибка: /private/path', code: 'new_backend_code', answer_language: 'ru' }, 500));
  api.setLanguage('en');
  await assert.rejects(api.request('/cart'), (error) => error.message.includes('try again later') && !error.message.includes('/private/path'));
});
test('network failures and validation fallback use the selected language', async () => {
  const api = new ApiClient('/api', async () => { throw new TypeError('offline'); });
  api.setLanguage('en');
  await assert.rejects(api.request('/cart'), (error) => error.code === 'network_error' && error.message.includes('Check your connection'));
  const invalid = new ApiClient('/api', async (url) => url.endsWith('/session') ? json({ session_id: 'one' }) : json({ detail: [{ input: 'private input' }] }, 422));
  invalid.setLanguage('kz');
  await assert.rejects(invalid.post('/agent/chat', {}), (error) => error.code === 'validation_error' && error.message.includes('4000') && !error.message.includes('private input'));
});
