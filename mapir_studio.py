"""PyInstaller entry-point for MapIR Studio.

This file exists purely as a launcher that imports the desktop app through
its proper package path. Running ``mapir/desktop/app.py`` directly fails for
relative imports — this file fixes that without changing the package layout.
"""

from __future__ import annotations

import sys

from mapir.desktop.app import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
