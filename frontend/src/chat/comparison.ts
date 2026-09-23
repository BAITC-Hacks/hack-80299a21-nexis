import type { ProductComparison } from './types';

interface ComparisonLabels {
  comparisonTitle: string; comparisonParameter: string; comparisonSame: string;
  comparisonDifferent: string; comparisonUnknown: string; comparisonIncomplete: string;
}

/** Catalog facts are text nodes. A comparison never creates or authorizes a cart action. */
export function renderComparison(comparison: ProductComparison | null | undefined, labels: ComparisonLabels, owner: Document = document): HTMLElement | null {
  if (!comparison || comparison.products.length < 2 || !comparison.rows.length) return null;
  const wrapper = owner.createElement('div');
  wrapper.className = 'product-comparison';
  wrapper.setAttribute('role', 'region');
  wrapper.setAttribute('aria-label', labels.comparisonTitle);
  wrapper.tabIndex = 0;
  const table = owner.createElement('table');
  const caption = owner.createElement('caption');
  caption.textContent = labels.comparisonTitle;
  table.append(caption);
  const head = owner.createElement('thead');
  const headingRow = owner.createElement('tr');
  for (const title of [labels.comparisonParameter, ...comparison.products.map((product) => product.name)]) {
    const cell = owner.createElement('th');
    cell.scope = 'col';
    cell.textContent = title;
    headingRow.append(cell);
  }
  head.append(headingRow);
  table.append(head);
  const body = owner.createElement('tbody');
  for (const row of comparison.rows) {
    const values = comparison.products.map((_, index) => typeof row.values[index] === 'string' ? row.values[index] : null);
    const incomplete = values.some((value) => value === null);
    const line = owner.createElement('tr');
    line.className = incomplete ? 'comparison-incomplete' : row.same ? 'comparison-same' : 'comparison-different';
    const label = owner.createElement('th');
    label.scope = 'row';
    const name = owner.createElement('span');
    name.textContent = row.label;
    const indicator = owner.createElement('small');
    indicator.className = 'comparison-indicator';
    indicator.textContent = incomplete ? labels.comparisonIncomplete : row.same ? labels.comparisonSame : labels.comparisonDifferent;
    label.append(name, indicator);
    line.append(label);
    for (const value of values) {
      const cell = owner.createElement('td');
      cell.textContent = value ?? labels.comparisonUnknown;
      if (value === null) cell.className = 'comparison-unknown';
      line.append(cell);
    }
    body.append(line);
  }
  table.append(body);
  wrapper.append(table);
  return wrapper;
}
