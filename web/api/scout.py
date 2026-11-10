"""Explicit serverless entrypoint; the implementation is shared in ``api.index``.

The class must be defined here rather than imported as an alias: the Vercel Python
builder only discovers a top-level ``handler`` class in the entrypoint file.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.index import handler as PublicHandler  # noqa: E402


class handler(PublicHandler):
    """Expose the shared synthetic-only handler under a discoverable class name."""
