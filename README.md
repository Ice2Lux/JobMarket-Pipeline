# azfr-spark-prefect-workflow-template

Python template for a spark workflow using prefect.


## Requirements

* Python >= 3.10

## How to use it

- To create python venv and install project's libraries:
> make venv

- To update venv after adding a lib in requirements.txt or requirements-dev.txt:
> make update

- For local tests, run the following:
> make test

## Spark support
```python
from azfr_prefect_utils.spark import spark_session
from azfr_prefect_utils.spark.config import SparkConfig
from prefect import task #,flow
...
#@flow
@task
def sample_function(spark_config: SparkConfig):
    with spark_session(spark_config, app_name="sample_app_name") as spark:
      # do your stuff with spark session
      spark.read.json('path/to/a/json/file')
      ...
```


## For more Information

