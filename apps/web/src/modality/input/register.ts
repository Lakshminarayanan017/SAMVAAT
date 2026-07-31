/**
 * Registers every input adapter, exactly once, at import time.
 *
 * Same shape as the output-side register: kept apart from both the registry and
 * ModalityInput so tests can populate adapters without mounting a tree.
 */
import { registerInputAdapter } from './registry';
import { AacBoardInput } from './adapters/AacBoardInput';
import { SignInput } from './adapters/SignInput';
import { SpeechInput } from './adapters/SpeechInput';
import { SwitchScanInput } from './adapters/SwitchScanInput';
import { TextInput } from './adapters/TextInput';

let registered = false;

export function registerAllInputAdapters(): void {
  if (registered) return;
  registered = true;

  registerInputAdapter('text', TextInput);
  registerInputAdapter('aac', AacBoardInput);
  registerInputAdapter('switch', SwitchScanInput);
  registerInputAdapter('speech', SpeechInput);
  registerInputAdapter('sign', SignInput);
}

registerAllInputAdapters();
