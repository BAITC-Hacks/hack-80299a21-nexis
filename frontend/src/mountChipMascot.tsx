import { createRoot } from 'react-dom/client';
import { ChipMascot, type ChipMascotState } from './components/ChipMascot';

export interface ChipMascotMount {
  setState: (state: ChipMascotState) => void;
}

let mountSequence = 0;

export function mountChipMascot(element: HTMLElement | null, size: number): ChipMascotMount {
  if (!element) return { setState: () => undefined };

  const root = createRoot(element, { identifierPrefix: `chip-mascot-${mountSequence++}-` });
  let state: ChipMascotState = 'idle';
  const render = () => root.render(<ChipMascot size={size} state={state} />);
  render();

  return {
    setState(nextState) {
      state = nextState;
      render();
    },
  };
}
