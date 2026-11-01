"""Ingest all weekly PSI zips in data/raw into data/bronze."""
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from pipeline.config import DATA_DIR

from pipeline.bronze import ingest_new_files

RAW_DIR = DATA_DIR / "raw"
EXTRACT_DIR = DATA_DIR / "extracted"
BRONZE_DIR = DATA_DIR / "bronze"


def extract_zips(raw_dir: Path, extract_dir: Path) -> list[Path]:
    """Unzip every weekly zip into its own folder and return all .DAT files."""
    for zip_path in sorted(raw_dir.glob("*.zip")):
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir / zip_path.stem)
    return sorted(extract_dir.rglob("*.DAT"))


def main() -> dict:
    ingested_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    dat_files = extract_zips(RAW_DIR, EXTRACT_DIR)
    ingested = ingest_new_files(dat_files, BRONZE_DIR, ingested_at)
    print(f"Found {len(dat_files)} .DAT files, ingested {len(ingested)} new or changed.")
    return {"dat_files": len(dat_files), "files_ingested": len(ingested)}


if __name__ == "__main__":
    main()