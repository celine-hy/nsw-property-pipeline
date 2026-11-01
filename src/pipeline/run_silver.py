"""Build silver sales from bronze: type, enrich, quality-check, deduplicate."""
from pathlib import Path
from pipeline.config import DATA_DIR

from pyspark.sql import functions as F

from pipeline.silver import dedupe_sales, enrich_sales, split_quality, type_sales
from pipeline.spark import get_spark

BRONZE_DIR = DATA_DIR / "bronze"
SALES_DIR = DATA_DIR / "silver" / "sales"
QUARANTINE_DIR = DATA_DIR / "silver" / "quarantine"


def main() -> dict:
    spark = get_spark()
    b, c, d = (spark.read.parquet(str(BRONZE_DIR / f"record_type={rt}")) for rt in "BCD")

    sales = enrich_sales(type_sales(b.drop("record_type", "record_index")), c, d)
    good, quarantine = split_quality(sales)
    silver = dedupe_sales(good).withColumn("contract_year", F.year("contract_date"))

    silver.write.mode("overwrite").partitionBy("contract_year").parquet(str(SALES_DIR))
    quarantine.write.mode("overwrite").parquet(str(QUARANTINE_DIR))

    total = b.count()
    quarantined = spark.read.parquet(str(QUARANTINE_DIR))
    n_quarantine = quarantined.count()
    n_silver = spark.read.parquet(str(SALES_DIR)).count()
    failed_rules = {
        r["rule"]: r["count"]
        for r in quarantined.select(F.explode("failed_rules").alias("rule"))
        .groupBy("rule").count().collect()
    }
    stats = {
        "bronze_sale_records": total,
        "quarantined": n_quarantine,
        "silver_sales": n_silver,
        "duplicates_removed": total - n_quarantine - n_silver,
        "failed_rules": failed_rules,
    }
    print(stats)
    return stats


if __name__ == "__main__":
    main()