"""Generate synthetic weekly PSI zip files for the public demo.

All suburbs, prices and ids are made up. The files use the real .DAT layout
(see docs/data-notes.md) and contain a fixed number of planted data problems,
so the pipeline's quality rules and deduplication can be shown and tested
without the licensed data.

Usage:
    PIPELINE_DATA_DIR=data_synthetic PYTHONPATH=src python -m pipeline.synthetic
"""
import argparse
import random
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

from pipeline.config import DATA_DIR

FILE_TYPE = "RTSALEDATA"
LEGAL_WIDTH = 70
NORMAL_SALES_PER_WEEK = 120

B_FIELDS = [
    "property_id", "sale_counter", "downloaded", "property_name", "unit_number",
    "house_number", "street_name", "locality", "post_code", "area", "area_type",
    "contract_date", "settlement_date", "price", "zoning", "nature",
    "primary_purpose", "strata_lot_number", "component_code", "sale_code",
    "pct_interest", "dealing_number",
]

SUBURBS = [  # (locality, post_code, district, typical price) - all made up
    ("NORTHVALE", "2901", "901", 650_000),
    ("RIVERTON", "2902", "901", 820_000),
    ("ELM HEIGHTS", "2903", "902", 1_200_000),
    ("SANDY BAY", "2904", "902", 950_000),
    ("RED GUM FLAT", "2905", "903", 380_000),
    ("KOOLA CREEK", "2906", "903", 520_000),
]
STREETS = ["MAIN ST", "BANKSIA AVE", "OCEAN RD", "WATTLE CL", "HILL ST"]


# ---------- .DAT lines ----------

def record(*fields) -> str:
    """Join fields into one .DAT line, ending with ';' like the real files."""
    return ";".join("" if f is None else str(f) for f in fields) + ";"


def header(district: str, downloaded: datetime) -> str:
    return record("A", FILE_TYPE, district, downloaded.strftime("%Y%m%d %H:%M"), "")


def trailer(lines: list[str]) -> str:
    """Z record: total includes A and Z, plus counts of B, C and D."""
    counts = {t: sum(line.startswith(t + ";") for line in lines) for t in "BCD"}
    return record("Z", len(lines) + 1, counts["B"], counts["C"], counts["D"])


def sale_lines(district: str, sale: dict) -> list[str]:
    """One sale -> its B line, C lines (legal text split at 70) and D lines."""
    key = (district, sale["property_id"], sale["sale_counter"], sale["downloaded"])
    b = record("B", district, *(sale.get(name) for name in B_FIELDS))
    legal = sale["legal_description"]
    c = [record("C", *key, legal[i:i + LEGAL_WIDTH]) for i in range(0, len(legal), LEGAL_WIDTH)]
    d = [record("D", *key, role, "", "", "", "", "") for role in sale["parties"]]
    return [b, *c, *d]


# ---------- one normal sale ----------

def ymd(day: date) -> str:
    return day.strftime("%Y%m%d")


def random_sale(rng: random.Random, week: date, counter: int, dealing: int) -> tuple[str, dict]:
    """A normal residential sale. Returns (district, sale)."""
    locality, post_code, district, typical = rng.choice(SUBURBS)
    settlement = week - timedelta(days=rng.randint(1, 14))
    contract = settlement - timedelta(days=rng.randint(28, 70))
    sale = {
        "property_id": str(rng.randint(1_000_000, 9_999_999)),
        "sale_counter": str(counter),
        "downloaded": ymd(week) + " 01:00",
        "house_number": str(rng.randint(1, 200)),
        "street_name": rng.choice(STREETS),
        "locality": locality,
        "post_code": post_code,
        "area": f"{rng.uniform(300, 900):.1f}",
        "area_type": "M",
        "contract_date": ymd(contract),
        "settlement_date": ymd(settlement),
        "price": str(int(round(typical * rng.lognormvariate(0, 0.25), -3))),
        "zoning": "R2",
        "nature": "R",
        "primary_purpose": "RESIDENCE",
        "dealing_number": f"SY{dealing:06d}",
        "legal_description": f"{rng.randint(1, 99)}/DP{rng.randint(100000, 999999)}",
        "parties": ["P", "V"],
    }
    return district, sale


# ---------- one week with planted problems ----------

class WeekBuilder:
    """Collects the sales of one week and hands out sale counters and dealing numbers."""

    def __init__(self, rng: random.Random, week: date, first_dealing: int):
        self.rng = rng
        self.week = week
        self.counter = 0
        self.dealing = first_dealing
        self.rows: list[tuple[str, dict]] = []

    def next_counter(self) -> str:
        self.counter += 1
        return str(self.counter)

    def new_sale(self, **overrides) -> tuple[str, dict]:
        """Add a normal sale with a new dealing number, then apply overrides."""
        self.dealing += 1
        district, sale = random_sale(self.rng, self.week, int(self.next_counter()), self.dealing)
        sale.update(overrides)
        self.rows.append((district, sale))
        return district, sale

    def repeat(self, district: str, sale: dict) -> None:
        """Write an existing sale again: same content, new counter and download time."""
        copy = dict(sale, sale_counter=self.next_counter(), downloaded=ymd(self.week) + " 01:00")
        self.rows.append((district, copy))


def build_week(rng: random.Random, week: date, first_dealing: int,
               previous_normal: list[tuple[str, dict]]) -> tuple[WeekBuilder, list, dict]:
    """Return the week's rows, its clean single sales (for next week's repeats) and planted counts."""
    wb = WeekBuilder(rng, week, first_dealing)
    normal = [wb.new_sale() for _ in range(NORMAL_SALES_PER_WEEK)]

    # Quality rule failures -> quarantine
    for _ in range(2):
        wb.new_sale(property_id="")
    wb.new_sale(contract_date="")
    wb.new_sale(contract_date="19760315")

    # Duplicates -> removed by deduplication
    wb.repeat(*normal[0])  # same sale twice in one file
    repeats = rng.sample(previous_normal, 2) if previous_normal else []
    for district, sale in repeats:  # re-published from last week
        wb.repeat(district, sale)

    # Strata: 3 lots in one dealing share property_id, differ by lot number
    district, first_lot = wb.new_sale(strata_lot_number="1", unit_number="1",
                                      legal_description="1/SP90001")
    for lot in ("2", "3"):
        wb.rows.append((district, dict(first_lot, sale_counter=wb.next_counter(),
                                       strata_lot_number=lot, unit_number=lot,
                                       legal_description=f"{lot}/SP90001")))

    # Multi-property dealing: 2 properties, each row repeats the total price
    district, first_prop = wb.new_sale()
    wb.rows.append((district, dict(first_prop, sale_counter=wb.next_counter(),
                                   property_id=str(rng.randint(1_000_000, 9_999_999)),
                                   house_number=str(int(first_prop["house_number"]) + 2))))

    # Late-arriving: contracts 1 to 3 years before the week
    for _ in range(2):
        old = week - timedelta(days=rng.randint(365, 3 * 365))
        wb.new_sale(contract_date=ymd(old))

    # Long legal description -> several C records joined in silver
    wb.new_sale(legal_description="LOT 7 SECTION 12 DP 765432 " * 4)

    # Rural vacant land measured in hectares
    wb.new_sale(area="12.5000", area_type="H", nature="V", zoning="RU1",
                primary_purpose="VACANT LAND")

    planted = {
        "b_records": len(wb.rows),
        "quarantine": 4,
        "duplicates": 1 + len(repeats),
    }
    return wb, normal, planted


# ---------- files ----------

def write_week(week: date, rows: list[tuple[str, dict]], raw_dir: Path) -> Path:
    """Write one zip with one .DAT file per district."""
    zip_path = raw_dir / f"{week:%Y%m%d}.zip"
    if zip_path.exists():
        raise FileExistsError(f"{zip_path} exists; refusing to overwrite (real data?)")
    downloaded = datetime.combine(week, datetime.min.time()).replace(hour=1)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for district in sorted({d for d, _ in rows}):
            lines = [header(district, downloaded)]
            for row_district, sale in rows:
                if row_district == district:
                    lines += sale_lines(district, sale)
            lines.append(trailer(lines))
            name = f"{district}_SALES_DATA_NNME_{week:%d%m%Y}.DAT"
            zf.writestr(name, "\n".join(lines) + "\n")
    return zip_path


def generate(weeks: int, seed: int, first_week: date, raw_dir: Path) -> dict:
    """Write `weeks` weekly zips and return the planted totals."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    totals = {"b_records": 0, "quarantine": 0, "duplicates": 0}
    previous_normal: list = []
    dealing = 0
    for i in range(weeks):
        week = first_week + timedelta(weeks=i)
        wb, previous_normal, planted = build_week(rng, week, dealing, previous_normal)
        dealing = wb.dealing
        write_week(week, wb.rows, raw_dir)
        for key in totals:
            totals[key] += planted[key]
    totals["silver"] = totals["b_records"] - totals["quarantine"] - totals["duplicates"]
    return totals


def main() -> dict:
    parser = argparse.ArgumentParser(description="Write synthetic weekly PSI zip files.")
    parser.add_argument("--weeks", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--first-week", type=date.fromisoformat, default=date(2026, 1, 5),
                        help="Monday of the first week, YYYY-MM-DD")
    args = parser.parse_args()
    totals = generate(args.weeks, args.seed, args.first_week, DATA_DIR / "raw")
    print(f"Wrote {args.weeks} synthetic weeks to {DATA_DIR / 'raw'}")
    print(f"Expected pipeline result: {totals}")
    return totals


if __name__ == "__main__":
    main()
