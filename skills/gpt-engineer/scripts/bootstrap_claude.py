#!/usr/bin/env python3
"""Claude-only wrapper for bootstrap.py."""

from __future__ import annotations

import sys

from bootstrap import main


if __name__ == "__main__":
    raise SystemExit(main(["--provider", "claude", *sys.argv[1:]]))
