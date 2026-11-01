import os

from pyspark.sql import SparkSession

SETTINGS = {
    "spark.sql.session.timeZone": "UTC",
    "spark.sql.legacy.timeParserPolicy": "CORRECTED",
    "spark.sql.ansi.enabled": "false",
}


def get_spark(app_name: str = "nsw-pipeline") -> SparkSession:
    """Return the platform session on Databricks, or a local session elsewhere."""
    if "DATABRICKS_RUNTIME_VERSION" in os.environ:
        spark = SparkSession.builder.getOrCreate()
        for key, value in SETTINGS.items():
            spark.conf.set(key, value)
        return spark

    builder = SparkSession.builder.appName(app_name).master("local[*]")
    builder = builder.config("spark.sql.shuffle.partitions", "4")
    for key, value in SETTINGS.items():
        builder = builder.config(key, value)
    return builder.getOrCreate()