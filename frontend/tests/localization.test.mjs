import test from 'node:test';
import assert from 'node:assert/strict';
import { storedLanguage, localizedError } from '../src/chat/localization.ts';
import { copy } from '../src/chat/i18n.ts';
import { storefrontCopy } from '../src/chat/storefront.ts';
import { renderClarification, renderKnowledgeSources } from '../src/chat/response.ts';
import { renderReasoningTimeline } from '../src/chat/reasoning.ts';

test('saved legacy kz and canonical kk both select the Kazakh interface', () => {
  assert.equal(storedLanguage('kz'), 'kz');
  assert.equal(storedLanguage('kk'), 'kz');
  assert.equal(storedLanguage('en'), 'en');
  assert.equal(storedLanguage('ru'), 'ru');
  assert.equal(storedLanguage(null), 'ru');
  assert.equal(storedLanguage('unknown'), 'ru');
});
test('English system copy has no Russian consultation fallback or inherited Cyrillic UI text', () => {
  const text = JSON.stringify({ chat: copy.en, storefront: storefrontCopy.en });
  assert.doesNotMatch(text, /[А-Яа-яЁё]/u);
  assert.doesNotMatch(text, /replies.*Russian|request \(Russian\)/i);
  assert.match(copy.en.promptQueries[2], /Payment/);
});
test('all languages provide each chat and storefront label', () => {
  for (const language of ['ru', 'kz', 'en']) {
    assert.deepEqual(Object.keys(copy[language]).sort(), Object.keys(copy.ru).sort());
    assert.deepEqual(Object.keys(storefrontCopy[language]).sort(), Object.keys(storefrontCopy.ru).sort());
  }
});
test('client-side rate-limit errors include Retry-After in all languages', () => {
  for (const language of ['ru', 'kz', 'en']) assert.ok(localizedError('rate_limited', language, { seconds: 12 }).includes('12'));
});
test('RAG sources preserve provenance, deduplicate chunks and never render unsafe links or markup', () => {
  const html = renderKnowledgeSources([
    { source_id: 'one', chunk_id: 'a', title: 'Payment <script>', source_url: 'https://ekt.kz/payment/', verified_at: '2026-09-23', page: 2 },
    { source_id: 'one', chunk_id: 'b', title: 'Payment <script>', source_url: 'https://ekt.kz/payment/', verified_at: '2026-09-23', page: 2 },
    { source_id: 'two', title: '<img src=x onerror=alert(1)>', source_url: 'javascript:alert(1)' },
  ], copy.en);
  assert.equal((html.match(/<li>/g) || []).length, 2);
  assert.match(html, /Answer sources/);
  assert.match(html, /Page: 2/);
  assert.match(html, /Checked: 2026-09-23/);
  assert.match(html, /https:\/\/ekt.kz\/payment\//);
  assert.doesNotMatch(html, /<script>|<img|javascript:/);
});
test('clarification is escaped and not repeated if already included in the answer', () => {
  const clarification = { kind: 'parameters', missing_fields: ['current'], message: 'Which current <A>?' };
  assert.equal(renderClarification(clarification, 'Which current <A>?', copy.en.clarification), '');
  assert.match(renderClarification(clarification, 'I can help.', copy.en.clarification), /Which current &lt;A&gt;\?/);
  assert.equal(renderClarification(null, '', copy.en.clarification), '');
});
test('timeline uses localized messages and never exposes raw tool output as UI prose', () => {
  const html = renderReasoningTimeline([{ type: 'tool_result', tool_name: 'search_products', tool_output: 'SECRET_TOOL_JSON' }], {
    title: copy.en.reasoning, fallback: copy.en.processing, count: String,
    types: {}, tools: { search_products: 'Catalog search' }, stateLabels: copy.en.reasoningStates,
  });
  assert.match(html, /Catalog search/);
  assert.doesNotMatch(html, /SECRET_TOOL_JSON|tool result|search_products/);
});
