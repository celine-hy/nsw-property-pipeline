"""Build the public GitHub Pages site from the synthetic pipeline output.

Reads the latest run report and the gold table, and writes one static page,
site/index.html, with no JavaScript and no external files.

Usage:
    PIPELINE_DATA_DIR=data_synthetic PYTHONPATH=src python -m pipeline.build_site
"""
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

import pandas as pd

from pipeline.config import DATA_DIR

SITE_DIR = Path("site")
REPO_URL = "https://github.com/celine-hy/nsw-property-pipeline"

CSS = """
:root { --bg: #fff; --fg: #1d1d1f; --muted: #6e6e73; --line: #e5e5ea; --bar: #0b72a3;
        --warn-bg: #fff4d6; --warn-fg: #6b4e00; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #161618; --fg: #f2f2f7; --muted: #a1a1a6; --line: #333336; --bar: #3aa0d8;
          --warn-bg: #3a3000; --warn-fg: #ffe08a; } }
body { margin: 0; background: var(--bg); color: var(--fg);
       font: 16px/1.5 -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 860px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 1.6rem; margin: 0 0 4px; }
h2 { font-size: 1.15rem; margin: 36px 0 12px; }
p.sub, footer { color: var(--muted); }
.warn { background: var(--warn-bg); color: var(--warn-fg); padding: 10px 14px; border-radius: 8px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
.card { border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; }
.card b { display: block; font-size: 1.5rem; }
.card span { color: var(--muted); font-size: .85rem; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.bar { background: var(--bar); height: 14px; border-radius: 3px; }
"""


def latest_report() -> dict:
    path = max((DATA_DIR / "reports").glob("run_*.json"))
    return json.loads(path.read_text())


def card(value, label: str) -> str:
    return f'<div class="card"><b>{value:,}</b><span>{escape(label)}</span></div>'


def money(value) -> str:
    return "–" if pd.isna(value) else f"${value:,.0f}"


def count(value) -> str:
    return "–" if pd.isna(value) else f"{int(value):,}"


def suburb_table(quarter: pd.DataFrame) -> str:
    """One row per suburb: a bar for sales count, then median price and its sample size."""
    top = quarter["sales_count"].max()
    rows = []
    for r in quarter.itertuples():
        width = 100 * r.sales_count / top
        rows.append(
            f"<tr><td>{escape(r.locality)}</td>"
            f'<td style="width:40%"><div class="bar" style="width:{width:.0f}%"></div></td>'
            f'<td class="num">{r.sales_count}</td>'
            f'<td class="num">{money(r.median_price)}</td>'
            f'<td class="num">{count(r.median_sample_size)}</td></tr>'
        )
    head = ('<tr><th>Suburb</th><th>Sales</th><th class="num">Count</th>'
            '<th class="num">Median price</th><th class="num">Sales used for median</th></tr>')
    return f"<table>{head}{''.join(rows)}</table>"


def build() -> Path:
    report = latest_report()
    silver = report["silver"]
    gold = pd.read_parquet(DATA_DIR / "gold" / "suburb_quarter")
    gold["contract_quarter"] = gold["contract_quarter"].astype(str)
    latest = gold["contract_quarter"].max()
    quarter = gold[gold["contract_quarter"] == latest].sort_values("sales_count", ascending=False)

    rules = "".join(
        f'<tr><td><code>{escape(rule)}</code></td><td class="num">{count}</td></tr>'
        for rule, count in silver["failed_rules"].items()
    )
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NSW Property Pipeline</title><style>{CSS}</style></head>
<body><main>
<h1>NSW Property Pipeline</h1>
<p class="sub">Bronze → silver → gold pipeline in PySpark, run end to end by GitHub Actions.</p>
<p class="warn"><b>Synthetic data.</b> Suburbs, prices and ids on this page are made up by
<code>pipeline.synthetic</code>, which copies the real NSW Valuer General file format and plants
known data problems. Real sales data is not published here because of its licence.</p>

<h2>Pipeline run</h2>
<div class="cards">
{card(silver["bronze_sale_records"], "sale records in bronze")}
{card(silver["quarantined"], "quarantined by quality rules")}
{card(silver["duplicates_removed"], "duplicates removed")}
{card(silver["silver_sales"], "clean sales in silver")}
{card(report["gold"]["dealings"], "dealings in gold")}
</div>
<p class="sub">Every number matches what the generator planted; the workflow fails if not.</p>

<h2>Quality rules that failed</h2>
<table><tr><th>Rule</th><th class="num">Rows quarantined</th></tr>{rules}</table>

<h2>Suburbs, contract quarter {escape(latest)}</h2>
{suburb_table(quarter)}
<p class="sub">Median uses single-property residential sales with 100% interest;
blank when fewer than 5 such sales.</p>

<h2>Incremental gold</h2>
<p>Quarters recomputed in this run: {escape(", ".join(report["gold"]["quarters_refreshed"]))}</p>

<footer><p>Built {built} · <a href="{REPO_URL}">Source code</a></p></footer>
</main></body></html>
"""
    SITE_DIR.mkdir(exist_ok=True)
    out = SITE_DIR / "index.html"
    out.write_text(page)
    return out


if __name__ == "__main__":
    print(f"Site written to {build()}")
