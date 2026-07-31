/**
 * The public surface of the modality layer.
 *
 * Feature code imports from here and gets exactly one thing: the router.
 * Renderers are deliberately NOT exported — an ESLint boundary rule blocks deep
 * imports into `renderers/`, so there is no supported way for a feature to pick
 * its own rendering. That is what stops accessibility decaying over six months
 * of ordinary feature work.
 */
export { ModalityRouter, type ModalityRouterProps } from './ModalityRouter';
export { registerAllRenderers } from './register';
