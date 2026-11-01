# Design decisions

## 2026-10-26 — Use a conda environment instead of venv
- **Context:** PySpark 3.5 only supports Java 8, 11 and 17. My Mac has Java 25 installed system-wide, and Python 3.11 was not installed.
- **Options:**
  1. venv + install Python 3.11 and Java 17 with Homebrew, then switch `JAVA_HOME` manually.
  2. conda environment with `python=3.11` and `openjdk=17` from conda-forge.
  3. Upgrade to PySpark 4.x, which supports newer Java.
- **Decision:** Option 2. Create the env with `conda create -n nsw-pipeline -c conda-forge python=3.11 openjdk=17`, then `pip install -r requirements.txt`.
- **Why / trade-offs:** Java 17 lives inside the project env and `JAVA_HOME` is set on activate, so the system Java 25 is untouched and setup is one command. The cost is that anyone running the project needs conda, and mixing conda and pip packages needs care (I only use conda for Python and Java, and pip for everything else).

## 2026-10-26 — Treat the data as CC BY-NC-ND 4.0
- **Context:** Sources disagree. The official bulk PSI page says CC BY-NC-ND 4.0; the government data catalogue (and reportedly a licence file inside the zips) says CC BY.
- **Options:** Follow CC BY (more permissive) or CC BY-NC-ND (stricter).
- **Decision:** Follow the stricter CC BY-NC-ND 4.0 stated on the official download page.
- **Why / trade-offs:** If I am wrong, the stricter reading is still safe. The cost: I cannot publish raw or processed data, so the repo has only code, docs, and my own charts.

## 2026-10-27 — Grain: property rows in silver, dealings in gold
- **Context:** One dealing can cover several properties, and every property row repeats the total price (96 of 96 multi-row dealings in week 20261019).
- **Options:** (1) Keep one row per B record everywhere. (2) Collapse to one row per dealing in silver. (3) Keep property rows in silver, aggregate by dealing in gold.
- **Decision:** Option 3.
- **Why / trade-offs:** Silver keeps all source detail. Gold counts each sale once. The cost is an extra aggregation step and two "grains" to explain.

## 2026-10-27 — Median prices use single-property residential sales only
- **Context:** Multi-property dealings carry a total price that cannot be split per property.
  Commercial and farm sales (nature_of_property = 3) dominate prices above $10M.
- **Decision:** Gold median price uses dealings with exactly one property, nature_of_property = R, and full interest (pct_interest empty). Volume counts all dealings.
- **Why / trade-offs:** The median reflects ordinary home prices. Excluded sales are still counted in volume and reported, not deleted.

## 2026-10-27 (revised 2026-10-30) — Deduplication key: (dealing_number, property_id, strata_lot_number), keep latest
- **Context:** Some dealings appear in two weekly files. Strata lots sold in one dealing share
  the same property_id and differ only by strata_lot_number (e.g. 7 units of one strata plan).
- **First attempt:** key (dealing_number, property_id) removed 221 rows on real data. 186 of
  them were distinct strata lots, not duplicates. unit_number is not reliable (two lots can
  share a unit number), so strata_lot_number is used.
- **Decision:** Key = (dealing_number, property_id, strata_lot_number). Keep the row with the
  latest download_datetime; ties broken by source_file. Rows with a missing key go to quarantine.
- **Result on 4 weeks:** 43 rows removed: 35 cross-week repeats and 8 exact duplicates inside
  one file (same sale written twice with different sale_counter). All 43 were identical rows.

## 2026-10-27 — Recompute every quarter touched by a new file
- **Context:** About 12% of a week's records have a contract date in an earlier year (late-arriving data).
- **Options:** (1) Only compute the current quarter. (2) Recompute all history every run.
  (3) Recompute only the quarters present in the new data.
- **Decision:** Option 3 for incremental runs; option 2 for a full backfill.
- **Why / trade-offs:** Past quarters stay correct as late sales arrive, without reprocessing all of history each week. Published past-quarter numbers can change, so the README should say so.

## 2026-10-28 — Bronze storage: Parquet, all columns as strings
- **Context:** Raw .DAT files are text. Later layers need fast, typed reads.
- **Options:** (1) Keep the .DAT text. (2) CSV. (3) Parquet.
- **Decision:** Parquet, with every column kept as a string in bronze.
- **Why / trade-offs:** Parquet is columnar, compressed and read natively by Spark.
  Strings keep bronze a faithful copy of the source (e.g. leading zeros in codes);
  type casting and validation happen in silver.

## 2026-10-28 — Bronze layout: one folder per record type, one file per source file
- **Decision:** `data/bronze/record_type=X/FILE_STEM.parquet` (X = A, B, C, D or Z;
  FILE_STEM = source file name without .DAT), with lineage columns `source_file` and
  `ingested_at` (UTC) on every row.
- **Why / trade-offs:** Record types have different columns, so they are separate tables.
  The Hive-style folder name lets Spark read `record_type` as a column. One output path
  per source file means a re-run overwrites instead of duplicating.

## 2026-10-28 — Incremental loads: manifest keyed on file name + SHA-256
- **Context:** New weekly files arrive, and a file could be republished with corrections
  under the same name.
- **Options:** (1) Reprocess everything each run. (2) Skip files by name. (3) Skip files by
  name + content hash.
- **Decision:** Option 3. `data/bronze/_manifest.csv` records source_file, sha256,
  ingested_at and b_rows.
- **Why / trade-offs:** Unchanged files are skipped; a corrected file has a new hash and is
  reprocessed. Hashing reads each file once per run, which is cheap at this size.
  Verified on 4 real weeks: 500 files, 14,069 B rows, second run ingests 0.

## 2026-10-30 — Silver: quarantine instead of delete
- **Decision:** Rows that break a hard rule (missing key or contract date, contract before
  2001, settlement before contract, price missing or not positive) are written to
  `data/silver/quarantine` with a `failed_rules` list. Suspicious but possible values
  (price under $10k, settlement over 365 days) stay in silver.
- **Why / trade-offs:** Bad rows stay traceable and countable, and can be reprocessed if a
  rule changes. Check on 4 weeks: 14,069 = 13,984 silver + 42 quarantined + 43 duplicates.

## 2026-10-30 — Silver: full rebuild, partitioned by contract year
- **Decision:** Silver is rebuilt from all bronze on every run (`mode("overwrite")`) and
  partitioned by `contract_year`.
- **Why / trade-offs:** At ~14k rows a full rebuild takes seconds and is idempotent by design.
  Deduplication needs all weeks together anyway. Revisit if data grows to many years.

## 2026-10-31 — Gold: dealings, contract quarter, median rules
- **Decision:** Gold first collapses silver property rows into one row per dealing, then
  computes per suburb and contract quarter: `sales_count` (all dealings) and `median_price`
  (single-property, residential, full-interest dealings only). The median is left empty when
  fewer than 5 such sales exist; `median_sample_size` is published next to it.
- **Why contract date:** The price is agreed at contract. Settlement is a median of 42 days
  later and sometimes over a year, which would put prices in the wrong quarter.
- **Why the minimum sample:** A median of one or two sales is noise, not a trend.

## 2026-10-31 — Gold: recompute only quarters touched by new loads
- **Context:** About 12% of a week's sales have a contract date in an earlier year.
- **Decision:** Gold records the (source_file, ingested_at) loads it has used. A run finds the
  quarters containing any sale from an unseen load and rewrites only those quarter partitions
  (`partitionOverwriteMode = dynamic`). A re-ingested corrected file has a new ingested_at, so
  its quarters are refreshed too.
- **Check:** On 4 weeks: first run rewrote 35 quarters, a re-run did nothing, and a simulated
  new load rewrote 1 quarter. Every run checks that gold sales_count adds up to the number of
  dealings in silver (13,656).
- **Trade-off:** Published numbers for past quarters can change when late sales arrive.