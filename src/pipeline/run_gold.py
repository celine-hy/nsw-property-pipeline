"""Build gold metrics from silver, recomputing only quarters touched by new loads."""
from pathlib import Path
from pipeline.config import DATA_DIR

import pandas as pd
from pyspark.sql import functions as F

from pipeline.gold import quarters_to_refresh, suburb_quarter_metrics, to_dealings
from pipeline.spark import get_spark

SILVER_DIR = DATA_DIR / "silver" / "sales"
METRICS_DIR = DATA_DIR / "gold" / "suburb_quarter"
PROCESSED_PATH = DATA_DIR / "gold" / "_processed_loads.csv"


def read_processed() -> set[tuple[str, str]]:
    """Return the (source_file, ingested_at) loads already reflected in gold."""
    if not PROCESSED_PATH.exists():
        return set()
    df = pd.read_csv(PROCESSED_PATH, dtype=str)
    return set(zip(df["source_file"], df["ingested_at"]))


def main() -> dict:
    spark = get_spark()
    sales = spark.read.parquet(str(SILVER_DIR))
    quarters = quarters_to_refresh(sales, read_processed())
    if not quarters:
        print("No new loads. Gold is up to date.")
        return {"quarters_refreshed": []}

    dealings = to_dealings(sales).filter(F.col("contract_quarter").isin(quarters))
    (suburb_quarter_metrics(dealings).write.mode("overwrite")
     .option("partitionOverwriteMode", "dynamic")
     .partitionBy("contract_quarter")
     .parquet(str(METRICS_DIR)))

    loads = [r.asDict() for r in sales.select("source_file", "ingested_at").distinct().collect()]
    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(loads).to_csv(PROCESSED_PATH, index=False)

    gold = spark.read.parquet(str(METRICS_DIR))
    silver_dealings = to_dealings(sales).count()
    gold_dealings = gold.agg(F.sum("sales_count")).first()[0]
    print(f"Quarters refreshed: {len(quarters)} ({quarters[0]} to {quarters[-1]})")
    print(f"Dealings in silver: {silver_dealings}, counted in gold: {gold_dealings}")
    if gold_dealings != silver_dealings:
        raise RuntimeError("Gold does not reconcile with silver")
    return {"quarters_refreshed": quarters, "dealings": silver_dealings}


if __name__ == "__main__":
    main()