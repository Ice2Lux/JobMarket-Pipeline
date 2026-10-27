from prefect import get_run_logger, task
import datetime

import azfr_fsspec_utils as fspath

from workflow.process.scrape_data import main as scrape_data



@task
def task_scrape_data(config):

    logger = get_run_logger()

    logger.info(f"Scraping de data depuis {config.base_url}...")
    _date_str = datetime.datetime.today().strftime('%Y%m%d')
    offres = scrape_data(config.auth_url, config.base_url, config.output_dir)
    logger.info(f"Dataframe résultant de taille: {len(offres)}")
    return offres
