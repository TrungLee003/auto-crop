import os
import sys
from pathlib import Path

# Automatically add bundled libvips binary directory on Windows if present
if sys.platform == "win32":
    vendor_dir = Path(__file__).resolve().parent.parent / "vendor"
    if vendor_dir.exists():
        for p in vendor_dir.glob("vips-dev*"):
            bin_dir = p / "bin"
            if bin_dir.is_dir():
                os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
                if hasattr(os, "add_dll_directory"):
                    try:
                        os.add_dll_directory(str(bin_dir))
                    except Exception:
                        pass
                break
