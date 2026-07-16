#!/usr/bin/env python3
"""Backward-compatible Codex-only wrapper for bootstrap.py."""

from __future__ import annotations

import sys
from bootstrap import main


if __name__ == "__main__":
    raise SystemExit(main(["--provider", "codex", *sys.argv[1:]]))
