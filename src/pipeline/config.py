"""Where pipeline data lives. Set PIPELINE_DATA_DIR to use another location."""
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("PIPELINE_DATA_DIR", "data"))