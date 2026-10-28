"""Usage: uv run python -m ingest [source ...]   (no sources = all). Exits 1 if any file failed."""

import logging
import sys

from ingest import EXTRACTORS
from ingest.base import run

# stdout, not stderr: Windows PowerShell 5.1 turns redirected native stderr into errors
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
names = sys.argv[1:] or list(EXTRACTORS)
unknown = set(names) - set(EXTRACTORS)
if unknown:
    sys.exit(
        f"unknown source(s): {', '.join(sorted(unknown))}; choose from {', '.join(EXTRACTORS)}"
    )
sys.exit(1 if run([EXTRACTORS[n]() for n in names]) else 0)
