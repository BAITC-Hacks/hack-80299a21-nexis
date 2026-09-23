import test from 'node:test';
import assert from 'node:assert/strict';
import { ApiClient, ApiError, apiLanguage } from '../src/chat/api.ts';

const json = (value, status = 200, headers = {}) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json', ...headers } });
const memory = () => {
  const entries = new Map();
  return { getItem: (k) => entries.get(k) || null, setItem: (k, v) => entries.set(k, v), removeItem: (k) => entries.delete(k) };
};

test('KZ maps to kk; English interface explicitly uses Russian consultation', () => {
  assert.equal(apiLanguage('kz'), 'kk');
  assert.equal(apiLanguage('ru'), 'ru');
  assert.equal(apiLanguage('en'), 'ru');
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
