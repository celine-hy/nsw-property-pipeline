# Problems log

## 2026-10-28 — Bronze did not pick up a schema change
- **Problem:** After adding `record_index` to bronze, re-running ingested 0 files.
- **Cause:** The manifest skips files whose name and hash are unchanged. The code changed, not the files.
- **Fix:** Deleted `data/bronze/` and re-ran (full rebuild). A schema change needs a backfill.

## 2026-10-30 — `fixture 'spark' not found`
- **Problem:** Silver tests could not find the shared Spark session.
- **Cause:** `tests/conftest.py` was missing or misnamed; pytest only loads that exact file name.
- **Fix:** Created `tests/conftest.py` with a session-scoped `spark` fixture.

## 2026-10-30 — `AssertionError` when importing silver.py
- **Problem:** Importing `silver.py` failed inside `F.col(...)`.
- **Cause:** In PySpark 3.5, `F.col` needs an active Spark session. The quality rules were built at
  module level, so they ran on import, before Spark started.
- **Fix:** Wrapped the rules in a function, `quality_rules()`, so they are built when called.

## 2026-10-30 — Deduplication removed real sales
- **Problem:** On real data, deduplication removed 221 rows; exploration suggested about 35.
- **Investigation:** Grouped the repeated keys by number of distinct download times. 35 keys spanned
  two weeks (true repeats). 157 keys were inside one file: several strata lots sold in one dealing
  share the same property_id and differ only by strata_lot_number. unit_number was not reliable.
- **Fix:** Key changed to (dealing_number, property_id, strata_lot_number). Removed rows dropped to
  43: 35 cross-week repeats and 8 sales written twice in the same file. Added a test for strata lots.

## 2026-10-30 — Rows missing from a diagnostic join
- **Problem:** A check listed 8 duplicate groups but the join showed only 1.
- **Cause:** In a Spark join, null never equals null. The other 7 groups had no strata_lot_number.
  (groupBy and window partitions do treat nulls as one group, so the deduplication itself was fine.)
- **Fix:** Filled nulls with a placeholder before joining in the diagnostic.

## 2026-10-31 — Charts showed as links in the README
- **Problem:** The README showed blue links instead of images.
- **Cause:** Markdown images need a leading `!`; without it they are links.
- **Fix:** Added `!` before both image lines.

## 2026-11-01 — Different Spark defaults on Databricks serverless
- **Problem:** Code that works locally can behave differently on Databricks serverless.
- **Cause:** Serverless runs with ANSI mode on by default. Under ANSI, a bad cast (for example a
  malformed date or number) raises an error instead of returning null, while the local session
  returns null and lets the quality rules quarantine the row.
- **Fix:** Found while preparing the move, before the first run. `get_spark()` now applies the same
  settings in both places (UTC time zone, `timeParserPolicy=CORRECTED`, `ansi.enabled=false`), so
  local and cloud results match.

## 2026-11-01 — `No module named 'pipeline'` in the Databricks notebook
- **Problem:** `from pipeline import run` failed in the notebook.
- **Cause:** The package lives in `src/pipeline/`. The notebook added the repo root to `sys.path`,
  not `src/`, so Python could not find the package.
- **Fix:** Added `<git folder>/src` to `sys.path`, the same thing `PYTHONPATH=src` does locally.

## 2026-11-01 — First Databricks run took 8 minutes
- **Problem:** The first full run took 8 minutes on Databricks. The next run took 2m23s, because
  bronze skipped the files it had already loaded.
- **Cause:** Bronze writes one small Parquet file per .DAT file and record type, about 2,500 files.
  Cloud storage has a high cost per file, so many tiny files are slow (the "small files problem").
- **Fix:** Not fixed yet. Results were correct, and the weekly job runtime is acceptable. Next step:
  write one bronze file per week and record type.

## 2026-11-01 — Badge broke after renaming the GitHub account
- **Problem:** After changing the GitHub username, the README tests badge still pointed to the old
  account name.
- **Cause:** GitHub redirects old repository URLs, but links written in files keep the old name.
- **Fix:** Searched the repo for the old name (`grep -rn`), updated the badge URL and the git remote.

