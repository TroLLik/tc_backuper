#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from urllib.error import HTTPError, URLError

import docker
from minio import Minio
from minio.error import BucketAlreadyExists, BucketAlreadyOwnedByYou, ResponseError
from prometheus_client import Gauge, start_http_server


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--tc_url", required=True)
    parser.add_argument("-u", "--tc_user", required=True)
    parser.add_argument("-p", "--tc_pwd", required=True)
    parser.add_argument("-m", "--minio_url", required=True)
    parser.add_argument("-a", "--minio_acc", required=True)
    parser.add_argument("-s", "--minio_sec", required=True)
    parser.add_argument("-c", "--backup_count", required=False, default=3)
    parser.add_argument("-i", "--backup_interval", required=False, default=300)
    return parser


class backup:
    def __init__(
        self, tc_url, tc_user, tc_pwd, minio_url, minio_acc, minio_sec, backup_count
    ):
        self.tc_url = tc_url
        self.tc_user = tc_user
        self.tc_pwd = tc_pwd
        self.minio_url = minio_url
        self.minio_acc = minio_acc
        self.minio_sec = minio_sec
        self.backup_count = backup_count
        self.file_name = "tc_backup"
        self.bucket_name = "backups"
        self.shared_volume = "/tmp/data/teamcity_server/datadir/"

    def check_backup_state(self):
        full_url = "http://" + self.tc_url + "/app/rest/server/backup"
        auth_user = self.tc_user
        auth_passwd = self.tc_pwd
        passman = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password(None, full_url, auth_user, auth_passwd)
        authhandler = urllib.request.HTTPBasicAuthHandler(passman)
        opener = urllib.request.build_opener(authhandler)

        urllib.request.install_opener(opener)
        try:
            req = urllib.request.Request(full_url)
            response = urllib.request.urlopen(req)
        except HTTPError as e:
            print("Error code: ", e.code)
            return False
        except URLError as e:
            print("Reason: ", e.reason)
            return False
        else:
            resp = response.read().decode("utf-8")
            if resp == "Idle":
                print("TC server are ready to backup:", resp)
                return True
            else:
                print("TC server are busy:", resp)
                return False

    def make_backup(self):
        full_url = (
            "http://"
            + self.tc_url
            + "/httpAuth/app/rest/server/backup?includeConfigs=true&includeDatabase=true&includeBuildLogs=false&fileName="
            + self.file_name
        )
        data = {}
        auth_user = self.tc_user
        auth_passwd = self.tc_pwd
        passman = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password(None, full_url, auth_user, auth_passwd)
        authhandler = urllib.request.HTTPBasicAuthHandler(passman)
        opener = urllib.request.build_opener(authhandler)
        urllib.request.install_opener(opener)
        data = urllib.parse.urlencode(data).encode()
        try:
            req = urllib.request.Request(full_url, data=data)
            response = urllib.request.urlopen(req)
        except HTTPError as e:
            print("Error code: ", e.code)
            return False
        except URLError as e:
            print("Reason: ", e.reason)
            return False
        else:
            return response.read().decode("utf-8")

    def put_backup_to_minio(self, backup_name):
        # Initialize minio_client with an endpoint and access/secret keys.
        minio_client = Minio(
            self.minio_url,
            access_key=self.minio_acc,
            secret_key=self.minio_sec,
            secure=False,
        )

        # Make a bucket with the make_bucket API call.
        try:
            minio_client.make_bucket(self.bucket_name, location="us-east-1")
        except BucketAlreadyOwnedByYou as err:
            pass
        except BucketAlreadyExists as err:
            pass

        while not os.path.exists(self.shared_volume + "backup/" + backup_name):
            time.sleep(1)
 
        try:
            if os.path.isfile(self.shared_volume + "backup/" + backup_name):            
                minio_client.fput_object(
                    self.bucket_name, backup_name, self.shared_volume + "backup/" + backup_name
                )
            else:
                raise ValueError("%s isn't a file!" % self.shared_volume + "backup/" + backup_name) 
        except ResponseError as err:
            print(err)
        except ValueError as err:
            print(err)
        else:
            print ('Backup file: ' + backup_name + ' was succesfully sended to minio')
            if os.path.exists(self.shared_volume + backup_name):
                os.remove(self.shared_volume + backup_name)
                print ('Backup file: ' + backup_name + ' was deleted')

    def pull_backup_from_minio(self, download_fname):
        minio_client = Minio(
            self.minio_url,
            access_key=self.minio_acc,
            secret_key=self.minio_sec,
            secure=False,
        )

        os.makedirs("/tmp/restored", exist_ok=True)

        # Get a full object
        try:
            minio_client.fget_object(
                self.bucket_name, download_fname, "/tmp/restored/" + download_fname
            )
        except ResponseError as err:
            print(err)

    def pull_last_backup_from_minio(self):
        minio_client = Minio(
            self.minio_url,
            access_key=self.minio_acc,
            secret_key=self.minio_sec,
            secure=False,
        )

        download_fname = self.get_minio_list()[0]

        print('File for pullin is: ' + download_fname)

        # Get a full object
        try:
            minio_client.fget_object(
                self.bucket_name, download_fname, "/tmp/restored/" + download_fname
            )
        except ResponseError as err:
            print(err)

        #file wait
        while not os.path.exists("/tmp/restored/" + download_fname):
            time.sleep(1)

        try:
            if os.path.isfile("/tmp/restored/" + download_fname):            
                return download_fname
            else:
                raise ValueError("%s isn't a file!" % "/tmp/restored/" + download_fname) 
        except ValueError as err:
            print(err)

    def get_minio_list(self):
        obj_list = []
        file_list = []
        minio_client = Minio(
            self.minio_url,
            access_key=self.minio_acc,
            secret_key=self.minio_sec,
            secure=False,
        )

        try:
            objects = minio_client.list_objects_v2(
                self.bucket_name, prefix=self.file_name, recursive=True
            )
            for obj in objects:
                obj_list.append(
                    [
                        datetime.timestamp(obj.last_modified),
                        obj.object_name.encode("utf-8"),
                    ]
                )
            obj_list.sort()
            obj_list.reverse()

            for i in obj_list:
                file_list.append(i[1].decode("utf-8"))
            return file_list
        except ResponseError as err:
            print(err)

    def del_minio_obj(self, rm_fname):
        minio_client = Minio(
            self.minio_url,
            access_key=self.minio_acc,
            secret_key=self.minio_sec,
            secure=False,
        )
        # Remove an object.
        try:
            minio_client.remove_object(self.bucket_name, rm_fname)
            print("Backup file", rm_fname, "was deleted")
        except ResponseError as err:
            print(err)

    def clean_minio_bucket(self):
        rm_fnames = self.get_minio_list()
        print(rm_fnames)

        for rm_fname in rm_fnames[int(self.backup_count):]:
            self.del_minio_obj(rm_fname=rm_fname)

    def restore_backup_from_minio(self, target_backup):
        client = docker.from_env()

        print ('This is the target backup file: ' + target_backup)

        container = client.containers.create('jetbrains/teamcity-server:latest',
                                        volumes={'/tmp/restored': {'bind': '/tmp/restored', 'mode': 'ro'}},
                                    detach=True,
                                    auto_remove=True)

        container.start()

        time.sleep(20)

        exec_log = container.exec_run("/opt/teamcity/bin/maintainDB.sh restore -A /data/teamcity_server/datadir -F /tmp/restored/" + target_backup,
                                        stdout=True,
                                        stderr=True,
                                        stream=True)        

        flag = False
        for line in exec_log[1]:

            if line == b"Restoring finished successfully.\n":
                flag = True
                print("Backup restoring finished successfully")

            #debug output
            #print(line, end='')
        container.stop()

        return flag


if __name__ == "__main__":

    parser = create_parser()
    param = parser.parse_args()

    print("Backup interval is: ", param.backup_interval)

    start_http_server(8000)
    g_backup = Gauge("tc_backup", "State of TeamCity backup")
    g_restore = Gauge("tc_restore", "State of TeamCity restore")

    while True:
        time.sleep(10)  # in seconds

        b = backup(
            tc_url=param.tc_url,
            tc_user=param.tc_user,
            tc_pwd=param.tc_pwd,
            minio_url=param.minio_url,
            minio_acc=param.minio_acc,
            minio_sec=param.minio_sec,
            backup_count=param.backup_count,
        )

        if b.check_backup_state():

            fname = b.make_backup() 
            #if restore return not false the g_backup should be set to 1
            if fname != False:
                g_backup.set(1)
            else:
                g_backup.set(0)

            b.put_backup_to_minio(backup_name=fname)
            b.clean_minio_bucket()
            
            l = b.pull_last_backup_from_minio()
            print ('The last restored backup: ' + l)

            #if restore return true the g_restore should be set to 1
            if b.restore_backup_from_minio(l):
                g_restore.set(1)
            else:
                g_restore.set(0)

        else:
            print('Backup failed')
            
        time.sleep(int(param.backup_interval))  # in seconds