"""Entry point that launches the Streamlit GUI via `promptvault-gui`."""
from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    try:
        from streamlit.web import cli as stcli
    except ImportError:
        print(
            "Streamlit is required to run the GUI.\n"
            "Install it with:  pip install 'promptvault[gui]'",
            file=sys.stderr,
        )
        sys.exit(1)

    gui_path = str(Path(__file__).parent / "gui.py")
    sys.argv = ["streamlit", "run", gui_path] + sys.argv[1:]
    sys.exit(stcli.main())
