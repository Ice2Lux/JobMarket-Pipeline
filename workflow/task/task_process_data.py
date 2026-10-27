from prefect import get_run_logger, task
import pandas as pd

from workflow.process.process_data import main as process_data


@task
def task_process_data(config, scraped_data: pd.DataFrame):

    logger = get_run_logger()

    logger.info("Processing des données scrappées...")
    cleaned_offres = process_data(scraped_data)
    logger.info(f"Transformation terminée : {len(cleaned_offres.columns)} colonnes finales.")
    return cleaned_offres
