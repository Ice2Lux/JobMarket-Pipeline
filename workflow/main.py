from prefect import flow
import pandas as pd

import azfr_fsspec_utils as fspath

from workflow.task.task_scrape_data import task_scrape_data
from workflow.task.task_process_data import task_process_data
from workflow.task.task_persist_data import task_persist_data
from workflow.config import WorkflowConfig



@flow(name="Pipeline ETL - Nettoyage + Persistance")
def main_flow(config: WorkflowConfig):

        csv_path = fspath.join(config.output_dir, "france_travail_offres_data_jobs.csv")

        if not fspath.exists(csv_path):
                offres = task_scrape_data(config)
        else:
                with fspath.open(csv_path, mode="r", encoding="utf-8") as f:
                        offres = pd.read_csv(f, sep=";", header=0)
        cleaned_offres = task_process_data(config, offres)
        task_persist_data(config, cleaned_offres)
