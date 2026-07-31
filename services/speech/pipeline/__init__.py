"""Speech pipeline stages (M6-M8).

Stage order:
    preprocess -> asr -> align -> gop -> prosody -> disfluency -> ppi

Each stage is a pure function over the previous stage output so any stage can be
evaluated in isolation by eval/harness.py.
"""
