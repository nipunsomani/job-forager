from __future__ import annotations

import sys
import io

# Reconfigure stdout/stderr to avoid UnicodeEncodeError on Windows
# where the default terminal encoding is cp1252.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True
    )

from jobforager.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
