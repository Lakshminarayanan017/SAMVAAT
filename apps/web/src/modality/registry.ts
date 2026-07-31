/**
 * The renderer registry.
 *
 * A renderer knows how to present ONE ContentBlock through ONE output channel.
 * Nothing else in the application may reach into this map — feature code renders
 * <ModalityRouter/>, and an ESLint boundary rule fails the build otherwise.
 *
 * That rule is the whole mechanism behind "accessibility as architecture"
 * (ADR-0001). A developer cannot forget to make a screen accessible, because
 * they never chose how it renders.
 */
import type { ReactNode } from 'react';
import type { CommunicationAbilityProfile, ContentBlock, OutputChannel } from '@samvaad/contracts';

export interface RendererProps {
  block: ContentBlock;
  profile: CommunicationAbilityProfile;
  /**
   * True when this renderer is a supporting channel beside a primary one — for
   * example pictographs shown under Easy-Read text. Supporting renderings are
   * visually quieter and are not announced separately, so a screen reader does
   * not read the same content three times.
   */
  isSupport?: boolean;
}

export type Renderer = (props: RendererProps) => ReactNode;

const registry = new Map<OutputChannel, Renderer>();

export function registerRenderer(channel: OutputChannel, renderer: Renderer): void {
  if (registry.has(channel)) {
    throw new Error(
      `A renderer for '${channel}' is already registered. Two renderers for one channel ` +
        'means the rendering a learner receives depends on module import order.',
    );
  }
  registry.set(channel, renderer);
}

export function getRenderer(channel: OutputChannel): Renderer | undefined {
  return registry.get(channel);
}

export function registeredChannels(): OutputChannel[] {
  return [...registry.keys()];
}

/** Test-only. Never call this from application code. */
export function __resetRegistry(): void {
  registry.clear();
}
