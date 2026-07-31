#!/usr/bin/env python
"""Build the minimal training package for Colab.

    python -m training.build_package

Produces `training/samvaad-training.zip`, containing only what the notebook must
import — chiefly `pipeline/disfluency.py`, so the features used in training are
byte-for-byte the ones the service uses at inference.

Deliberately minimal. Uploading the whole repository to Colab would mean the
notebook could quietly import something that is not actually deployed, and the
resulting train/serve skew is invisible until it is expensive.
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

SPEECH = Path(__file__).resolve().parent.parent
OUTPUT = SPEECH / "training" / "samvaad-training.zip"

#: Everything the notebook imports, and nothing else.
INCLUDE = [
    "pipeline/__init__.py",
    "pipeline/disfluency.py",
]

MANIFEST = """SAMVAAD — disfluency training package
=====================================

Contents
--------
pipeline/disfluency.py   the feature extractor, label schema and coaching library

Why this file exists
--------------------
`extract_features` here is the SAME function the production service calls at
inference time. Training on features that differ from the ones served is one of
the most common and most invisible ML bugs: the model scores well in the
notebook and behaves randomly in production, and nothing errors.

Do not edit this copy. If a feature needs changing, change it in the repository
at services/speech/pipeline/disfluency.py, rebuild this package, and retrain.

Usage
-----
Upload this zip when the Colab notebook asks (Cell 4). The notebook unpacks it
and imports from it directly.

Integrity
---------
{checksums}
"""


def main() -> int:
    entries = []

    for relative in INCLUDE:
        path = SPEECH / relative
        if not path.exists():
            raise SystemExit(f"missing: {relative}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        entries.append(f"  {digest}  {relative}")

    manifest = MANIFEST.format(checksums="\n".join(entries))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in INCLUDE:
            archive.write(SPEECH / relative, relative)
        archive.writestr("README.txt", manifest)

    size = OUTPUT.stat().st_size
    print(f"built {OUTPUT.name}  ({size:,} bytes)")
    for relative in INCLUDE:
        print(f"  {relative}")
    print("  README.txt")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
