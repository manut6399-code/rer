#!/usr/bin/env python3
"""RepoRadar single-file launcher. Works from any directory.

Usage: python repodar.py --help
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from reporadar.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
