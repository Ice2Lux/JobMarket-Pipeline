import azfr_fsspec_utils as fspath
import pyspark.sql.functions as F
from prefect import get_run_logger
from pyspark.sql import DataFrame


def write_deltalake(data: DataFrame, output_name: str, output_dir: str, date_str: str):
    logger = get_run_logger()
    out_dir = fspath.join(output_dir, output_name)
    data = data.withColumn("__version__", F.lit(date_str))
    logger.info(f'Writing leaders in deltalake format {out_dir}, partition: {date_str}')
    data.write.format("delta").mode("overwrite").partitionBy("__version__").save(out_dir)
    return out_dir