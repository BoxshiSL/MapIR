"""MapIR Studio — PySide6 desktop application.

Entry points::

    python -m mapir.cli desktop          # launch the studio window
    python -m mapir.cli desktop --no-browser   # headless smoke / CI

Importing this package does *not* require PySide6 to be installed; sub-modules
import Qt lazily so that the CLI keeps working even on minimal installs.
"""

from __future__ import annotations
