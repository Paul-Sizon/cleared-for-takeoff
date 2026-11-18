#!/usr/bin/env python3
"""App Store preflight scanner. Usage: python3 preflight.py <project-or-ipa> [--json] [--ci]"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preflight.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
