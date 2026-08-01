/**
 * Stack — layout without magic numbers.
 *
 * Spacing is the thing that drifts fastest across screens, because `1rem` and
 * `0.9rem` look identical in isolation and nobody notices until ten screens
 * disagree. Making the gap a token forces the choice into a small set.
 *
 * Horizontal stacks wrap by default (`ui.css`). At 400% zoom a 1280px viewport
 * behaves as 320px, and a row of three buttons that does not wrap is a WCAG
 * 1.4.10 reflow failure. Wrapping being the default means forgetting it is not
 * possible.
 */
import type { CSSProperties, ElementType, ReactNode } from 'react';

import { GAP, mergeStyles, type Gap } from './styles';

export interface StackProps {
  direction?: 'vertical' | 'horizontal';
  gap?: Gap;
  align?: CSSProperties['alignItems'];
  justify?: CSSProperties['justifyContent'];
  /** Renders as something other than a div — `ul`, `section`, `nav`. */
  as?: ElementType;
  style?: CSSProperties;
  children: ReactNode;
}

export function Stack({
  direction = 'vertical',
  gap = 'md',
  align,
  justify,
  as: Component = 'div',
  style,
  children,
  ...rest
}: StackProps & Record<string, unknown>) {
  return (
    <Component
      {...rest}
      data-ui="stack"
      data-direction={direction}
      style={mergeStyles(
        {
          display: 'flex',
          flexDirection: direction === 'vertical' ? 'column' : 'row',
          gap: GAP[gap],
          alignItems: align,
          justifyContent: justify,
        },
        style,
      )}
    >
      {children}
    </Component>
  );
}

/**
 * A responsive grid that never needs a media query.
 *
 * `auto-fit` + `minmax` reflows at every viewport and every zoom level without
 * breakpoints, which matters because zoom is a first-class breakpoint here
 * (§11) and media queries do not fire on zoom in the way people expect.
 */
export function Grid({
  min = '16rem',
  gap = 'md',
  as: Component = 'div',
  style,
  children,
  ...rest
}: {
  min?: string;
  gap?: Gap;
  as?: ElementType;
  style?: CSSProperties;
  children: ReactNode;
} & Record<string, unknown>) {
  return (
    <Component
      {...rest}
      data-ui="grid"
      style={mergeStyles(
        {
          display: 'grid',
          gridTemplateColumns: `repeat(auto-fit, minmax(min(${min}, 100%), 1fr))`,
          gap: GAP[gap],
        },
        style,
      )}
    >
      {children}
    </Component>
  );
}
