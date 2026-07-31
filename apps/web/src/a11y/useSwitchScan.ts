/**
 * Switch scanning.
 *
 * A learner with severe motor impairment (P3, Arjun) cannot point. They operate
 * one or two physical switches — often a head switch or a large button. The
 * interface highlights each option in turn, and the switch selects.
 *
 * Two modes, from the profile:
 *
 *   2-switch (default)  switch A advances the highlight, switch B selects.
 *                       NO TIMER AT ALL. The learner controls the pace entirely.
 *
 *   1-switch            the highlight advances automatically every `dwellMs`,
 *                       and the single switch selects.
 *
 * On Ethics E6 (no time-pressure mechanics): the 1-switch dwell is a *scanning
 * affordance the learner configures for themselves*, not a difficulty mechanic
 * imposed by us. Nothing expires, nothing is scored lower for taking longer, and
 * the sequence loops forever. The distinction matters, and 2-switch — which has
 * no timing at all — is the default precisely so timing is opt-in.
 *
 * Switches present themselves to the browser as key presses, which is how
 * commercial switch interfaces work. Defaults are Space and Enter.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

export interface SwitchScanOptions {
  /** Number of scannable items. Scanning restarts if this changes. */
  itemCount: number;
  enabled: boolean;
  switchCount?: 1 | 2;
  dwellMs?: number;
  onSelect: (index: number) => void;
  /** Announce the highlighted item, so scanning works without sight too. */
  onFocusChange?: (index: number) => void;
  advanceKey?: string;
  selectKey?: string;
}

export interface SwitchScanState {
  /** Index currently highlighted, or -1 when scanning is off. */
  activeIndex: number;
  advance: () => void;
  select: () => void;
  isScanning: boolean;
}

export function useSwitchScan({
  itemCount,
  enabled,
  switchCount = 2,
  dwellMs = 1200,
  onSelect,
  onFocusChange,
  advanceKey = ' ',
  selectKey = 'Enter',
}: SwitchScanOptions): SwitchScanState {
  const [activeIndex, setActiveIndex] = useState(enabled && itemCount > 0 ? 0 : -1);

  // Held in refs so the keydown listener and the dwell timer always see current
  // values without being torn down and rebuilt on every render.
  const activeRef = useRef(activeIndex);
  const selectRef = useRef(onSelect);
  const focusRef = useRef(onFocusChange);

  activeRef.current = activeIndex;
  selectRef.current = onSelect;
  focusRef.current = onFocusChange;

  const setActive = useCallback((index: number) => {
    setActiveIndex(index);
    activeRef.current = index;
    focusRef.current?.(index);
  }, []);

  const advance = useCallback(() => {
    if (itemCount <= 0) return;
    // Wraps forever. A scan that stops at the end strands a learner who missed
    // their target and has no way back.
    setActive((activeRef.current + 1) % itemCount);
  }, [itemCount, setActive]);

  const select = useCallback(() => {
    const index = activeRef.current;
    if (index >= 0 && index < itemCount) selectRef.current(index);
  }, [itemCount]);

  // Reset when scanning turns on, or when the set of items changes underneath.
  useEffect(() => {
    if (!enabled || itemCount <= 0) {
      setActiveIndex(-1);
      activeRef.current = -1;
      return;
    }
    setActive(0);
  }, [enabled, itemCount, setActive]);

  // Auto-advance, 1-switch only. 2-switch never starts a timer.
  useEffect(() => {
    if (!enabled || switchCount !== 1 || itemCount <= 0) return;

    const timer = window.setInterval(advance, dwellMs);
    return () => window.clearInterval(timer);
  }, [enabled, switchCount, dwellMs, itemCount, advance]);

  useEffect(() => {
    if (!enabled || itemCount <= 0) return;

    const onKeyDown = (event: KeyboardEvent) => {
      // Never hijack keys while the learner is typing. A switch user may also
      // have a keyboard, and swallowing Space inside a text field would make
      // writing an answer impossible.
      if (isTextEntry(event.target)) return;

      if (event.key === selectKey || (switchCount === 1 && event.key === advanceKey)) {
        event.preventDefault();
        select();
        return;
      }

      if (switchCount === 2 && event.key === advanceKey) {
        event.preventDefault();
        advance();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [enabled, itemCount, switchCount, advanceKey, selectKey, advance, select]);

  return { activeIndex, advance, select, isScanning: enabled && itemCount > 0 };
}

function isTextEntry(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable;
}

/** Reads the scanning settings out of a profile, with safe defaults. */
export function switchScanSettings(profile: {
  interaction?: { switch_scanning?: { enabled?: boolean; switch_count?: number; dwell_ms?: number } | null } | null;
}): { enabled: boolean; switchCount: 1 | 2; dwellMs: number } {
  const scanning = profile.interaction?.switch_scanning;
  return {
    enabled: scanning?.enabled === true,
    switchCount: scanning?.switch_count === 1 ? 1 : 2,
    dwellMs: scanning?.dwell_ms ?? 1200,
  };
}
