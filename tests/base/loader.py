# coding: utf-8

import logging

import azfr_fsspec_utils

logger = logging.getLogger(__name__)


class TestLoader(object):

    def __init__(self, test_dir, target_dir):
        self.test_dir = test_dir
        self.target_dir = target_dir

    def root_dir(self):
        return self.target_dir

    @classmethod
    def mk_dirs_with_file_system(cls, file_system, folder, raise_if_exists=True):
        file_system.mkdir(folder, raise_if_exists=raise_if_exists)

    @classmethod
    def mk_dirs(cls, folder):
        azfr_fsspec_utils.makedirs(folder, exist_ok=True)

    def path(self, path):
        return azfr_fsspec_utils.join(self.test_dir, path)

    def dest(self, path, target_dir=None):
        if target_dir is not None:
            target_dir = target_dir.format(self.target_dir)
        else:
            target_dir = self.target_dir
        result = azfr_fsspec_utils.join(target_dir, path)
        return result

    def copy_path_with_file_system(self, file_system, path, dest=None):
        src = self.path(path)
        dest = self.dest(dest or path)

        self.mk_dirs_with_file_system(file_system, azfr_fsspec_utils.dirname(dest))
        file_system.copy(src, dest)

        return dest

    def copy_path(self, path, dest=None):
        src = self.path(path)
        dest = self.dest(path) if dest is None else dest
        self.mk_dirs(azfr_fsspec_utils.dirname(dest))
        azfr_fsspec_utils.copy(src, dest)
        return dest