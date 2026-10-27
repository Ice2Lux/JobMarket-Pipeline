from prefect import get_run_logger, task
import pandas as pd
import datetime

from workflow.utils.utils import write_deltalake

OUTPUT_NAME = "offres"

@task
def task_persist_data(config, cleaned_data: pd.DataFrame):
    """Écrit le DataFrame au format Delta Lake."""

    logger = get_run_logger()

    _date_str = datetime.datetime.today().strftime('%Y%m%d')
    logger.info(f"Persistance en cours vers {config.output_dir}/{OUTPUT_NAME} pour {_date_str}")

    write_deltalake(cleaned_data, OUTPUT_NAME, config.output_dir, _date_str)
    logger.info("Persistance terminée avec succès!")
