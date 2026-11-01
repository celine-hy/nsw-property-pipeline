"""Run the whole pipeline (bronze -> silver -> gold) and save a run report."""
import json
from datetime import datetime, timezone
from pathlib import Path
from pipeline.config import DATA_DIR

from pipeline import run_bronze, run_gold, run_silver

REPORT_DIR = DATA_DIR / "reports"


def main() -> None:
    started_at = datetime.now(timezone.utc)
    report = {
        "started_at": started_at.isoformat(timespec="seconds"),
        "bronze": run_bronze.main(),
        "silver": run_silver.main(),
        "gold": run_gold.main(),
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"run_{started_at:%Y%m%dT%H%M%SZ}.json"
    path.write_text(json.dumps(report, indent=2))
    print(f"Report saved to {path}")


if __name__ == "__main__":
    main()