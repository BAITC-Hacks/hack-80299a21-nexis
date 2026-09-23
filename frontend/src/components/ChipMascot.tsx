import { useId } from 'react';

export type ChipMascotState = 'idle' | 'thinking' | 'success';

export interface ChipMascotProps {
  state?: ChipMascotState;
  size?: number;
  className?: string;
}

const stateLabels: Record<ChipMascotState, string> = {
  idle: 'ChipAI is ready',
  thinking: 'ChipAI is thinking',
  success: 'ChipAI found an answer',
};

export function ChipMascot({ state = 'idle', size = 64, className = '' }: ChipMascotProps) {
  const rawId = useId();
  const id = rawId.replace(/:/g, '');

  return (
    <svg
      aria-label={stateLabels[state]}
      className={`chip-mascot chip-mascot--${state} block select-none ${className}`.trim()}
      height={size}
      role="img"
      viewBox="0 0 120 120"
      width={size}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id={`chip-metal-${id}`} x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stopColor="#334155" />
          <stop offset="0.48" stopColor="#1e293b" />
          <stop offset="1" stopColor="#0f172a" />
        </linearGradient>
        <linearGradient id={`chip-gold-${id}`} x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stopColor="#fde68a" />
          <stop offset="0.52" stopColor="#fbbf24" />
          <stop offset="1" stopColor="#d97706" />
        </linearGradient>
        <filter height="180%" id={`chip-glow-${id}`} width="180%" x="-40%" y="-40%">
          <feGaussianBlur result="blur" stdDeviation="2.8" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <g className="chip-mascot__body">
        <g className="chip-mascot__pins" fill={`url(#chip-gold-${id})`} stroke="#b7791f" strokeWidth="1.2">
          <rect height="13" rx="3" width="17" x="8" y="25" />
          <rect height="13" rx="3" width="17" x="8" y="47" />
          <rect height="13" rx="3" width="17" x="8" y="69" />
          <rect height="13" rx="3" width="17" x="8" y="91" />
          <rect height="13" rx="3" width="17" x="95" y="25" />
          <rect height="13" rx="3" width="17" x="95" y="47" />
          <rect height="13" rx="3" width="17" x="95" y="69" />
          <rect height="13" rx="3" width="17" x="95" y="91" />
        </g>
        <rect fill={`url(#chip-metal-${id})`} height="84" rx="19" stroke="#475569" strokeWidth="2" width="82" x="19" y="18" />
        <path d="M31 31V27Q31 25 34 25H86" fill="none" opacity=".48" stroke="#94a3b8" strokeLinecap="round" strokeWidth="2" />
        <rect fill="#07111f" height="45" rx="12" stroke="#3b536d" strokeWidth="1.5" width="62" x="29" y="48" />
        <path d="M36 56H84" opacity=".3" stroke="#64748b" strokeLinecap="round" />

        <g className="chip-mascot__bolt" filter={`url(#chip-glow-${id})`}>
          <path d="M62 25 52 39h7l-2 10 12-16h-8l2-8Z" fill="#fb923c" stroke="#fdba74" strokeLinejoin="round" strokeWidth="1.5" />
        </g>

        {state === 'success' ? (
          <g className="chip-mascot__eyes chip-mascot__eyes--happy" fill="none" filter={`url(#chip-glow-${id})`} stroke="#38bdf8" strokeLinecap="round" strokeLinejoin="round" strokeWidth="4">
            <path d="M39 75q7-10 14 0" />
            <path d="M67 75q7-10 14 0" />
          </g>
        ) : (
          <g className="chip-mascot__eyes" fill="none" filter={`url(#chip-glow-${id})`} stroke="#38bdf8" strokeLinecap="round" strokeWidth="4">
            <circle className="chip-mascot__eye" cx="46" cy="72" r="5.5" />
            <circle className="chip-mascot__eye" cx="74" cy="72" r="5.5" />
            <ellipse className="chip-mascot__pupil" cx="46" cy="72" fill="#7dd3fc" rx="2.2" ry="1.5" stroke="none" />
            <ellipse className="chip-mascot__pupil" cx="74" cy="72" fill="#7dd3fc" rx="2.2" ry="1.5" stroke="none" />
          </g>
        )}
        <path className="chip-mascot__smile" d="M51 84q9 7 18 0" fill="none" stroke="#67e8f9" strokeLinecap="round" strokeWidth="2.5" />
        <circle cx="25" cy="20" r="2" fill="#94a3b8" opacity=".8" />
        <circle cx="95" cy="100" r="2" fill="#94a3b8" opacity=".8" />
      </g>
    </svg>
  );
}

export default ChipMascot;
