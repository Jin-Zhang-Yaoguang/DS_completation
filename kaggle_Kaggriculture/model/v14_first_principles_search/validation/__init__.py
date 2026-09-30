"""V14 fail-closed dual-anchor validation protocol.

The protocol scripts are intentionally executable both as direct files and as
package modules.  Adding this directory to ``sys.path`` keeps their sealed
direct-script imports identical in both modes.
"""

from pathlib import Path
import sys


_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

