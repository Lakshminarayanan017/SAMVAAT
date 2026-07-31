/**
 * Registers every renderer, exactly once, at import time.
 *
 * Kept separate from the registry itself so the registry has no dependency on
 * the renderers, and separate from ModalityRouter so tests can populate the
 * registry without mounting a component tree.
 *
 * Adding an output channel means: add the enum value in common.schema.json, add
 * a fallback entry in contracts/src/guards.ts, write the renderer, register it
 * here. Miss the last step and the router logs a clear error rather than
 * rendering a blank screen.
 */
import { registerRenderer } from './registry';
import { AudioRenderer } from './renderers/AudioRenderer';
import { CaptionedTextRenderer } from './renderers/CaptionedTextRenderer';
import { EasyReadRenderer } from './renderers/EasyReadRenderer';
import { IslRenderer } from './renderers/IslRenderer';
import { PictographRenderer } from './renderers/PictographRenderer';

let registered = false;

export function registerAllRenderers(): void {
  if (registered) return;
  registered = true;

  registerRenderer('captioned_text', CaptionedTextRenderer);
  registerRenderer('audio', AudioRenderer);
  registerRenderer('easy_read', EasyReadRenderer);
  registerRenderer('pictograph', PictographRenderer);
  registerRenderer('isl', IslRenderer);
}

registerAllRenderers();
