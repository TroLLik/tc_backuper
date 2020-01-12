#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from unittest import mock

import os
import sys
sys.path.insert(0, os.path.abspath('.'))

print (sys.path)

from com.tc_backuper.main.app import backup

class TCbackupTestCase(unittest.TestCase):

    def setUp(self):
        self.backup = backup(
            tc_url="some_url",
            tc_user="some_user",
            tc_pwd="some_password",
            minio_url="some_url",
            minio_acc="some_acc",
            minio_sec="some_sec",
            backup_count=3
        )

    def test_check_backup_state_idle(self):
        with mock.patch("urllib.request.urlopen") as response_mock:
            response_mock.return_value.read.return_value.decode.return_value = "Idle"

            result = self.backup.check_backup_state()

            self.assertTrue(result)

    def test_check_backup_state_busy(self):
        with mock.patch("urllib.request.urlopen") as response_mock:
            response_mock.return_value.read.return_value.decode.return_value = "Fail"

            result = self.backup.check_backup_state()

            self.assertFalse(result)

    def test_put_backup_to_minio(self):
        backup_name = "my_backup"

        with mock.patch("os.path.exists") as exists_mock:
            exists_mock.return_value = "True"

            with mock.patch("os.path.isfile") as isfile_mock:
                isfile_mock.return_value = "True"

                with mock.patch("os.remove") as remove_mock:
                    remove_mock.return_value = "True"

                    with mock.patch("com.tc_backuper.main.app.Minio") as minio_mock:
                        minio_client = minio_mock.return_value

                        self.backup.put_backup_to_minio(backup_name)

                        minio_client.fput_object.assert_called_with(
                            self.backup.bucket_name,
                            backup_name,
                            self.backup.shared_volume + 'backup/' + backup_name
                        )

    def test_pull_backup_from_minio(self):
        backup_name = "my_backup"

        with mock.patch("com.tc_backuper.main.app.Minio") as minio_mock:
            minio_client = minio_mock.return_value

            self.backup.pull_backup_from_minio(backup_name)

            minio_client.fget_object.assert_called_with(
                self.backup.bucket_name,
                backup_name,
                "/tmp/restored/" + backup_name
            )

    def test_pull_last_backup_from_minio(self):
        backup_name = "last_backup"

        with mock.patch("os.path.exists") as exists_mock:
            exists_mock.return_value = "True"

            with mock.patch("os.path.isfile") as isfile_mock:
                isfile_mock.return_value = "True"        

                with mock.patch("com.tc_backuper.main.app.Minio") as minio_mock:
                    minio_client = minio_mock.return_value

                    # mock get_minio_list
                    with mock.patch.object(backup, "get_minio_list", return_value=[backup_name]):
                        # get pull_last_backup_from_minio
                        last_backup = self.backup.pull_last_backup_from_minio()

                    self.assertEqual(last_backup, backup_name)

                    minio_client.fget_object.assert_called_with(
                        self.backup.bucket_name,
                        backup_name,
                        "/tmp/restored/" + backup_name
                    )

    def test_make_backup_fail(self):
        with mock.patch("urllib.request.urlopen") as response_mock:
            response_mock.return_value.read.return_value.decode.return_value = False

            result = self.backup.make_backup()

            self.assertFalse(result)

    def test_make_backup_success(self):
        with mock.patch("urllib.request.urlopen") as response_mock:
            response_mock.return_value.read.return_value.decode.return_value = self.backup.file_name

            result = self.backup.make_backup()

            self.assertTrue(result)

    def test_get_minio_list(self):
        with mock.patch("com.tc_backuper.main.app.Minio") as minio_mock:
            minio_client = minio_mock.return_value

            self.backup.get_minio_list()

            minio_client.list_objects_v2.assert_called_with(
                self.backup.bucket_name,
                prefix=self.backup.file_name,
                recursive=True
            )

    def test_del_minio_obj(self):
        rm_file_name = "my_rm_file"

        with mock.patch("com.tc_backuper.main.app.Minio") as minio_mock:
            minio_client = minio_mock.return_value

            self.backup.del_minio_obj(rm_file_name)

            minio_client.remove_object.assert_called_with(
                self.backup.bucket_name,
                rm_file_name
            )

    def test_clean_minio_bucket(self):
        extra_backup = "last_backup"
        backup_names=['my_rm_file_name1', 'my_rm_file_name2', 'my_rm_file_name3', extra_backup]

        # mock del_minio_obj
        with mock.patch.object(backup, "del_minio_obj") as del_minio_obj:
            with mock.patch.object(backup, "get_minio_list", return_value=backup_names):
                self.backup.clean_minio_bucket()

            del_minio_obj.assert_called_with(
                rm_fname=extra_backup
            )
            self.assertEqual(del_minio_obj.call_count, len(backup_names) - self.backup.backup_count)

if __name__ == '__main__':
    unittest.main()
