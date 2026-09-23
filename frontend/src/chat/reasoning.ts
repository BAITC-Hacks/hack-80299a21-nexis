import { escapeHtml } from './dom';
import type { ReasoningStep } from './types';

interface ReasoningLabels {
  title: string;
  fallback: string;
  count: (count: number) => string;
  types: Record<string, string>;
  stateLabels: Record<StepState, string>;
}

type StepState = 'complete' | 'active' | 'pending' | 'error';

function stepState(step: ReasoningStep): StepState {
  const status = step.status?.toLowerCase();
  if (status === 'error' || status === 'failed' || status === 'cancelled') return 'error';
  if (status === 'pending' || status === 'queued' || status === 'waiting') return 'pending';
  if (status === 'running' || status === 'active' || status === 'in_progress' || status === 'processing') return 'active';
  if (step.completed === false) return 'pending';
  if (status && !['done', 'complete', 'completed', 'success', 'succeeded'].includes(status)) return 'pending';
  // A final API trace without an explicit status describes work already returned.
  return 'complete';
}

export function renderReasoningTimeline(steps: ReasoningStep[], labels: ReasoningLabels, live = false): string {
  if (!steps.length) return '';
  const completed = steps.filter((step) => stepState(step) === 'complete').length;
  const progress = completed / steps.length;
  const rows = steps.map((step) => {
    const state = stepState(step);
    const label = step.message || (typeof step.tool_output === 'string' ? step.tool_output : '') || step.tool_name || labels.fallback;
    const type = step.type ? `<span class="reasoning-type">${escapeHtml(labels.types[step.type] || step.type.replaceAll('_', ' '))}</span>` : '';
    const icon = state === 'complete' ? '<svg class="icon"><use href="#i-check"></use></svg>' : state === 'error' ? '!' : '<span class="reasoning-step-dot"></span>';
    return `<li class="reasoning-step is-${state}"><span class="reasoning-step-icon" aria-hidden="true">${icon}</span><span class="reasoning-step-copy">${type}<span class="visually-hidden">${escapeHtml(labels.stateLabels[state])}: </span><span>${escapeHtml(label)}</span></span></li>`;
  }).join('');
  const progressAttributes = live ? 'aria-busy="true"' : `aria-valuenow="${Math.round(progress * 100)}"`;
  return `<details class="reasoning${live ? ' reasoning-live' : ''}"${live ? ' open' : ''}><summary><svg class="icon"><use href="#i-spark"></use></svg><span>${escapeHtml(labels.title)}</span><span class="reasoning-count">${escapeHtml(labels.count(steps.length))}</span><svg class="icon reasoning-chevron"><use href="#i-chevron"></use></svg></summary><div class="reasoning-progress" role="progressbar" aria-label="${escapeHtml(labels.title)}" aria-valuemin="0" aria-valuemax="100" ${progressAttributes}><span class="reasoning-progress-fill" style="transform:scaleX(${progress})"></span></div><ol class="reasoning-list">${rows}</ol></details>`;
}
