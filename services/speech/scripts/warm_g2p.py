#!/usr/bin/env python
"""Download the corpora phonemisation needs, then prove they work.

    python -m scripts.warm_g2p

Run this once after `pip install -r requirements.txt`, and in CI and the Docker
build before the service starts taking traffic. g2p_en fetches its NLTK corpora
lazily on first call, which means the first learner to record something pays for
a download — or, on a host with no outbound network, gets a stage that silently
reports itself unavailable.

Exit code 0 means GOP can run on this host. Non-zero means it cannot, and the
service will say so through `/capabilities` rather than failing per request.
"""

from __future__ import annotations

import sys


def main() -> int:
    from pipeline import g2p

    if not g2p.ensure_nltk_data():
        print("NLTK corpora could not be downloaded. Phonemisation is unavailable.")
        print("The service still boots; /capabilities will report gop=false.")
        return 1

    # Construction is not proof. Phonemising a real phrase is.
    phones = g2p.phoneme_string("Could you please repeat that?")
    # ASCII only: this runs in Docker builds and Windows consoles, and a
    # UnicodeEncodeError from a status message is an absurd way to fail a build.
    print(f"g2p ready - {phones}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
