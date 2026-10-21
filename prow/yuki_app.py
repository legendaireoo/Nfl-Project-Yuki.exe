"""YUKI.exe: double-click -> the results page opens in the default browser. No data or Python needed."""
import os
import shutil
import sys
import tempfile
import webbrowser
from pathlib import Path

REPORT = "YUKI_report.html"


def main():
    src = Path(getattr(sys, "_MEIPASS", Path(__file__).parent / "output")) / REPORT
    exe_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    for target_dir in (exe_dir, Path(tempfile.gettempdir())):  # next to the exe, else %TEMP%
        try:
            dst = target_dir / REPORT
            shutil.copyfile(src, dst)
            break
        except OSError:
            continue
    if not webbrowser.open(dst.as_uri()):
        os.startfile(dst)


if __name__ == "__main__":
    main()
