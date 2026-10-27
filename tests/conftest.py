# coding: utf-8
import os

import azfr_fsspec_utils
import pytest

from tests.base.loader import TestLoader

CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
TEST_DIR = os.path.abspath(os.path.dirname(CURRENT_DIR))
TARGET_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../target"))
TARGET_TEST = os.path.abspath(os.path.join(TARGET_DIR, "tests"))


def _paths(request):
    path = "{}".format(request.fspath)
    folder, file = os.path.split(path)
    test_dir = azfr_fsspec_utils.abspath(folder)
    rel_path = azfr_fsspec_utils.relpath(test_dir, TEST_DIR)
    target_dir = azfr_fsspec_utils.abspath(
        azfr_fsspec_utils.join(
            TARGET_DIR, rel_path, file.replace(".py", ""), request.function.__name__),
    )
    return test_dir, target_dir


@pytest.fixture(scope='session')
def remove_test_data():
    paths = [
        'file://{}',
    ]
    for path in paths:
        uri = path.format(TARGET_DIR)
        try:
            azfr_fsspec_utils.removedirs(path=uri)
        except FileNotFoundError:
            pass


@pytest.fixture(autouse=True)
def loader(request):
    test_dir, target_dir = _paths(request)
    azfr_fsspec_utils.removedirs(target_dir, ignore_errors=True)
    loader = TestLoader(
        test_dir=test_dir,
        target_dir=target_dir,
    )

    request.cls.loader = loader
    return loader
