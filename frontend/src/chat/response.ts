import { escapeHtml } from './dom.ts';
import { productUrl } from './products.ts';
import type { Clarification, KnowledgeSource } from './types';

interface SourceLabels { sources: string; checkedAt: string; sourcePage: string }
/** Only catalog/knowledge URLs returned by the server are rendered; document text is never HTML. */
export function renderKnowledgeSources(sources: KnowledgeSource[], labels: SourceLabels): string {
  const seen = new Set<string>();
  const entries = sources.flatMap((source) => {
    const url = productUrl(source.source_url);
    const identity = `${source.source_id || source.id || url || source.title}:${source.page || ''}`;
    if (!source.title || seen.has(identity)) return [];
    seen.add(identity);
    const title = url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.title)}</a>` : escapeHtml(source.title);
    const metadata: string[] = [];
    if (source.page && Number.isInteger(source.page) && source.page > 0) metadata.push(`${labels.sourcePage}: ${source.page}`);
    if (source.verified_at && !Number.isNaN(Date.parse(source.verified_at))) metadata.push(`${labels.checkedAt}: ${source.verified_at.slice(0, 10)}`);
    return [`<li>${title}${metadata.length ? `<small>${escapeHtml(metadata.join(' · '))}</small>` : ''}</li>`];
  });
  return entries.length ? `<details class="knowledge-sources"><summary>${escapeHtml(labels.sources)}</summary><ul>${entries.join('')}</ul></details>` : '';
}
export function renderClarification(clarification: Clarification | null | undefined, answer: string, label: string): string {
  if (!clarification?.message || answer.includes(clarification.message)) return '';
  return `<aside class="clarification"><strong>${escapeHtml(label)}</strong><p>${escapeHtml(clarification.message)}</p></aside>`;
}
