import test from 'node:test';
import assert from 'node:assert/strict';
import { renderComparison } from '../src/chat/comparison.ts';
import { copy } from '../src/chat/i18n.ts';

// A minimal DOM double checks construction through textContent, not HTML parsing.
class Element {
  constructor(tagName) { this.tagName = tagName; this.children = []; this.attributes = {}; this.text = ''; }
  set textContent(value) { this.text = String(value); this.children = []; }
  get textContent() { return this.text + this.children.map((child) => child.textContent).join(''); }
  set innerHTML(_) { throw Error('Comparison content must use text nodes'); }
  setAttribute(name, value) { this.attributes[name] = value; }
  append(...children) { this.children.push(...children); }
}
const owner = { createElement: (tag) => new Element(tag) };
const find = (element, tag) => [ ...(element.tagName === tag ? [element] : []), ...element.children.flatMap((child) => find(child, tag)) ];
const products = [{ id: 1, name: 'Legrand <script>alert(1)</script>' }, { id: 2, name: 'IEK 200300285_' }];

test('comparison table uses text nodes and retains original names, labels and values', () => {
  const input = { products, rows: [{ key: 'current', label: 'Rated current', values: ['160 A', '250 A'], same: false }] };
  const before = JSON.stringify(input);
  const table = renderComparison(input, copy.en, owner);
  assert.equal(table.attributes.role, 'region');
  assert.equal(table.attributes['aria-label'], copy.en.comparisonTitle);
  assert.equal(table.tabIndex, 0);
  assert.equal(find(table, 'caption')[0].textContent, 'Product comparison');
  const columns = find(table, 'th').filter((cell) => cell.scope === 'col');
  assert.deepEqual(columns.map((cell) => cell.textContent), ['Parameter', ...products.map((product) => product.name)]);
  assert.deepEqual(find(table, 'td').map((cell) => cell.textContent), ['160 A', '250 A']);
  assert.equal(find(table, 'script').length, 0);
  assert.equal(find(table, 'button').length, 0);
  assert.equal(find(table, 'form').length, 0);
  assert.equal(JSON.stringify(input), before);
});
test('comparison indicators and unknown cells are localized on all three languages', () => {
  for (const language of ['ru', 'kz', 'en']) {
    const labels = copy[language];
    const table = renderComparison({ products, rows: [
      { key: 'same', label: 'A', values: ['3', '3'], same: true },
      { key: 'different', label: 'B', values: ['3', '2'], same: false },
      { key: 'unknown', label: 'C', values: [null, '3'], same: false },
    ] }, labels, owner);
    assert.deepEqual(find(table, 'small').map((cell) => cell.textContent), [labels.comparisonSame, labels.comparisonDifferent, labels.comparisonIncomplete]);
    assert.equal(find(table, 'td')[4].textContent, labels.comparisonUnknown);
    assert.equal(find(table, 'tbody')[0].children[2].className, 'comparison-incomplete');
  }
});
test('missing comparison values remain unknown without introducing extra columns', () => {
  const table = renderComparison({ products, rows: [
    { key: 'missing', label: 'Missing', values: ['0'], same: true },
    { key: 'extra', label: 'Extra', values: ['1', '2', 'not-a-product'], same: false },
  ] }, copy.en, owner);
  assert.deepEqual(find(table, 'td').map((cell) => cell.textContent), ['0', 'Unknown', '1', '2']);
  assert.equal(find(table, 'small')[0].textContent, 'Insufficient data');
});
test('empty or single-product comparisons do not render a misleading table', () => {
  assert.equal(renderComparison(null, copy.en, owner), null);
  assert.equal(renderComparison(undefined, copy.en, owner), null);
  assert.equal(renderComparison({ products, rows: [] }, copy.en, owner), null);
  assert.equal(renderComparison({ products: products.slice(0, 1), rows: [{ key: 'x', label: 'X', values: ['1'], same: true }] }, copy.en, owner), null);
});
