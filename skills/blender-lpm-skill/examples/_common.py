"""Shared bootstrap for example recipes: run through bl.py, e.g.
   python scripts/bl.py --script examples/gladius.py -- --out _work/lpm/gladius
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))
import lpm  # noqa: E402


def out_stem(default):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--out" in argv:
        return argv[argv.index("--out") + 1]
    return default
