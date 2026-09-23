import { useId } from 'react';
import './ChipMascot.css';

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

const pinPositions = [29, 44, 59, 74, 89];

/** An OLED microchip. All motion lives in CSS and respects reduced motion. */
export function ChipMascot({ state = 'idle', size = 64, className = '' }: ChipMascotProps) {
  const id = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const paint = (name: string) => `url(#chip-${name}-${id})`;

  return (
    <span
      aria-label={stateLabels[state]}
      className={`chip-mascot chip-mascot--${state} ${className}`.trim()}
      role="img"
      style={{ width: size, height: size }}
    >
      <svg aria-hidden="true" className="chip-mascot__art" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id={`chip-bevel-${id}`} x1="0" x2="1" y1="0" y2="1">
            <stop stopColor="#9aadc4" />
            <stop offset=".22" stopColor="#43516d" />
            <stop offset=".6" stopColor="#162238" />
            <stop offset="1" stopColor="#637a96" />
          </linearGradient>
          <linearGradient id={`chip-body-${id}`} x1="0" x2=".85" y1="0" y2="1">
            <stop stopColor="#293650" />
            <stop offset=".48" stopColor="#0f172a" />
            <stop offset="1" stopColor="#0a1120" />
          </linearGradient>
          <linearGradient id={`chip-gold-${id}`} x1="0" x2="0" y1="0" y2="1">
            <stop stopColor="#ffecb0" />
            <stop offset=".35" stopColor="#e9bd63" />
            <stop offset=".7" stopColor="#a7732d" />
            <stop offset="1" stopColor="#f8d98c" />
          </linearGradient>
          <linearGradient id={`chip-screen-${id}`} x1="0" x2="1" y1="0" y2="1">
            <stop stopColor="#020911" />
            <stop offset="1" stopColor="#061929" />
          </linearGradient>
          <linearGradient id={`chip-glass-${id}`} x1="0" x2=".7" y1="0" y2="1">
            <stop stopColor="#a5e8ff" stopOpacity=".12" />
            <stop offset="1" stopColor="#a5e8ff" stopOpacity="0" />
          </linearGradient>
          <filter height="200%" id={`chip-glow-${id}`} width="200%" x="-50%" y="-50%">
            <feGaussianBlur result="blur" stdDeviation="1.8" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        <g className="chip-mascot__body">
          <g fill={paint('gold')} stroke="#8a622c" strokeWidth=".6">
            {pinPositions.map((y) => (
              <g key={y}>
                <rect height="8" rx="2" width="17" x="6" y={y} />
                <rect height="8" rx="2" width="17" x="97" y={y} />
              </g>
            ))}
          </g>

          <rect fill="#020617" height="87" rx="19" width="84" x="18" y="19" />
          <rect fill={paint('bevel')} height="87" rx="19" width="84" x="18" y="16" />
          <rect fill={paint('body')} height="81" rx="16" width="78" x="21" y="19" />
          <path d="M27 36v-4a8 8 0 0 1 8-8h43" fill="none" opacity=".6" stroke="#8294b2" strokeLinecap="round" />
          <path d="M30 97h54a11 11 0 0 0 11-11V45" fill="none" opacity=".4" stroke="#050b15" strokeWidth="2" />

          <g fill="none" opacity=".45" stroke="#6593af" strokeWidth=".8">
            <path d="M23 46h5m-5 14h5m-5 14h5m64-28h5m-5 14h5m-5 14h5" />
            <path d="M36 34h12l4-4h14" />
          </g>
          <circle cx="34" cy="33" fill="#67e8f9" opacity=".8" r="1.5" />

          <rect fill="#020617" height="49" rx="12" width="66" x="27" y="40" />
          <rect fill={paint('screen')} height="46" rx="10" stroke="#406078" strokeWidth=".8" width="62" x="29" y="41" />
          <path d="M40 43h39a9 9 0 0 1 9 9v5L32 73V51a8 8 0 0 1 8-8Z" fill={paint('glass')} />

          <g className="chip-mascot__face" key={state} filter={paint('glow')}>
            {state === 'thinking' ? (
              <g fill="none" stroke="#67e8f9" strokeLinecap="round" strokeWidth="2.5">
                {[46, 74].map((cx) => (
                  <g className="chip-mascot__radar" key={cx}>
                    <circle cx={cx} cy="63" opacity=".15" r="7" strokeWidth="1" />
                    <path d={`M${cx - 7} 63a7 7 0 0 1 7-7m7 7a7 7 0 0 1-7 7`} />
                    <circle cx={cx} cy="63" fill="#cffafe" r="1.5" stroke="none" />
                  </g>
                ))}
              </g>
            ) : state === 'success' ? (
              <g fill="none" stroke="#a5f3fc" strokeLinecap="round" strokeWidth="3.5">
                <path d="M39 66q7-11 14 0M67 66q7-11 14 0" />
              </g>
            ) : (
              <g className="chip-mascot__eyes" fill="#a5f3fc">
                <rect height="12" rx="3.5" width="6.5" x="42.75" y="56" />
                <rect height="12" rx="3.5" width="6.5" x="70.75" y="56" />
              </g>
            )}
            <path
              className="chip-mascot__smile"
              d={state === 'thinking' ? 'M55 77h10' : 'M52 75q8 7 16 0'}
              fill="none"
              stroke="#67e8f9"
              strokeLinecap="round"
              strokeWidth="2"
            />
          </g>

          <g className="chip-mascot__bolt" filter={paint('glow')}>
            <path d="m87 22-7 10h5l-2 8 11-13h-6l3-5Z" fill="#f59e0b" stroke="#ffe5a4" strokeLinejoin="round" strokeWidth=".7" />
          </g>
          {state === 'success' && (
            <g className="chip-mascot__spark" fill="none" stroke="#fbbf24" strokeLinecap="round" strokeWidth="1.6">
              <path d="m95 17 3-4m1 11 6-1m-4 9 4 3M81 16l-1-4" />
            </g>
          )}

          <g fill="#7a8da9">
            <circle cx="33" cy="94" opacity=".6" r="1.1" />
            <circle cx="87" cy="94" opacity=".6" r="1.1" />
            <rect height="1" opacity=".6" rx=".5" width="16" x="52" y="94" />
          </g>
        </g>
      </svg>
    </span>
  );
}

export default ChipMascot;
