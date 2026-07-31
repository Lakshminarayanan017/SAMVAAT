/**
 * Switch scanning behaviour.
 *
 * P3 (Arjun) depends entirely on this. The properties asserted here are the
 * difference between a usable interface and one he cannot operate at all.
 */
import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { switchScanSettings, useSwitchScan } from '@/a11y/useSwitchScan';

afterEach(() => {
  vi.useRealTimers();
});

function press(key: string, target?: EventTarget) {
  act(() => {
    const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true });
    (target ?? window).dispatchEvent(event);
  });
}

describe('2-switch mode (the default)', () => {
  it('never starts a timer — the learner controls the pace entirely', () => {
    vi.useFakeTimers();
    const onSelect = vi.fn();

    const { result } = renderHook(() =>
      useSwitchScan({ itemCount: 3, enabled: true, switchCount: 2, onSelect }),
    );

    expect(result.current.activeIndex).toBe(0);

    // A very long time passes. Nothing moves, nothing expires, nothing is lost.
    act(() => {
      vi.advanceTimersByTime(10 * 60 * 1000);
    });

    expect(result.current.activeIndex).toBe(0);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('advances on switch 1 and selects on switch 2', () => {
    const onSelect = vi.fn();
    const { result } = renderHook(() =>
      useSwitchScan({ itemCount: 3, enabled: true, switchCount: 2, onSelect }),
    );

    press(' ');
    expect(result.current.activeIndex).toBe(1);

    press(' ');
    expect(result.current.activeIndex).toBe(2);

    press('Enter');
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it('wraps forever, so a missed target is always reachable again', () => {
    const { result } = renderHook(() =>
      useSwitchScan({ itemCount: 3, enabled: true, switchCount: 2, onSelect: vi.fn() }),
    );

    press(' ');
    press(' ');
    press(' ');

    // Back to the start rather than stranded at the end.
    expect(result.current.activeIndex).toBe(0);
  });
});

describe('1-switch mode', () => {
  it('advances automatically at the learner-configured dwell', () => {
    vi.useFakeTimers();

    const { result } = renderHook(() =>
      useSwitchScan({
        itemCount: 3,
        enabled: true,
        switchCount: 1,
        dwellMs: 1000,
        onSelect: vi.fn(),
      }),
    );

    expect(result.current.activeIndex).toBe(0);
    act(() => void vi.advanceTimersByTime(1000));
    expect(result.current.activeIndex).toBe(1);
    act(() => void vi.advanceTimersByTime(1000));
    expect(result.current.activeIndex).toBe(2);
  });

  it('selects with the single switch', () => {
    const onSelect = vi.fn();
    renderHook(() =>
      useSwitchScan({ itemCount: 3, enabled: true, switchCount: 1, onSelect }),
    );

    press(' ');
    expect(onSelect).toHaveBeenCalledWith(0);
  });
});

describe('coexisting with a keyboard', () => {
  it('does not swallow keys while the learner is typing', () => {
    const onSelect = vi.fn();
    const { result } = renderHook(() =>
      useSwitchScan({ itemCount: 3, enabled: true, switchCount: 2, onSelect }),
    );

    // A switch user may also have a keyboard. Hijacking Space inside a text
    // field would make writing an answer impossible.
    const textarea = document.createElement('textarea');
    document.body.appendChild(textarea);
    press(' ', textarea);

    expect(result.current.activeIndex).toBe(0);
    expect(onSelect).not.toHaveBeenCalled();
    textarea.remove();
  });

  it('is inert when the profile has not enabled scanning', () => {
    const onSelect = vi.fn();
    const { result } = renderHook(() =>
      useSwitchScan({ itemCount: 3, enabled: false, onSelect }),
    );

    expect(result.current.activeIndex).toBe(-1);
    press(' ');
    press('Enter');
    expect(onSelect).not.toHaveBeenCalled();
  });
});

describe('switchScanSettings', () => {
  it('defaults to 2-switch, the mode with no timing at all', () => {
    expect(switchScanSettings({})).toEqual({ enabled: false, switchCount: 2, dwellMs: 1200 });
  });

  it('reads the profile when scanning is configured', () => {
    expect(
      switchScanSettings({
        interaction: { switch_scanning: { enabled: true, switch_count: 1, dwell_ms: 2500 } },
      }),
    ).toEqual({ enabled: true, switchCount: 1, dwellMs: 2500 });
  });
});
