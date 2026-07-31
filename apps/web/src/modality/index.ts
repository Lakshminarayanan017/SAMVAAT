/**
 * The public surface of the modality layer.
 *
 * Feature code imports from here and gets exactly two things: the output router
 * and the input router. Renderers and adapters are deliberately NOT exported —
 * an ESLint boundary rule blocks deep imports into `renderers/` and
 * `input/adapters/`, so there is no supported way for a feature to pick its own
 * presentation or its own input method.
 *
 * That is what stops accessibility decaying over six months of ordinary feature
 * work: it is not a convention anyone has to remember, it is a build failure.
 */
export { ModalityRouter, type ModalityRouterProps } from './ModalityRouter';
export { registerAllRenderers } from './register';

export { ModalityInput, type ModalityInputProps } from './input/ModalityInput';
export { registerAllInputAdapters } from './input/register';
export type { Transcriber } from './input/adapters/SpeechInput';
