import os

import azfr_fsspec_abfs
from uuid_extensions import uuid7str

azfr_fsspec_abfs.use()
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))

WF_RUN_ID = uuid7str()
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY")
GITHUB_SHA = os.environ.get("GITHUB_SHA")