#!/usr/bin/env python3
"""Compatibility entry point for the production UI smoke suite.

The V3 harness is authoritative. This module remains as a stable filename for
older deployment references while delegating to the corrected implementation.
"""
from __future__ import annotations

from production_ui_smoke_v3 import main


if __name__ == "__main__":
    raise SystemExit(main())
