# coding: utf-8

import os

TEST_DATA_DIR = os.path.abspath(os.path.dirname(__file__))

TARGET_DIR = os.path.abspath(os.path.join(TEST_DATA_DIR, "../../target"))
TARGET_TEST = os.path.abspath(os.path.join(TARGET_DIR, "tests"))
TARGET_TMP_DIR = os.path.abspath(os.path.join(TARGET_TEST, "tmp"))
