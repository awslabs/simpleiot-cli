#!/usr/bin/env python

# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
# This command is used to load up the digital twin file and the datapoint
# values.
#
# Use this to upload the generated USDZ, GLB, or GLTB file up to S3, then
# mark its location into the model record.
#
# You can also use this to indicate the position for each datapoint on the
# 3D model.
#

import click
from simpleiot.common.utils import make_api_request, show_detail, format_date
from simpleiot.common.config import *

import urllib, urllib.parse
from rich import print
from rich.console import Console
from rich.table import Table
import boto3
from boto3.s3.transfer import S3Transfer
import os, sys, threading

console = Console()

#
# This class updates upload progress and displays it on the console.
#
class UploadProgress(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)" % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            sys.stdout.flush()


@click.group()
def twin():
    """Manage Digital 3D Twin files"""


@twin.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--model", help="Model name", envvar="IOT_MODEL", required=True)
@click.option("--file", "--input", help="USDZ/GLB/GLTF local file", required=True)
def file(team, profile, project, model, file):
    """
    Upload 3D Twin file to secure project bucket
    \f
    Examples:

    $ iot twin file --project="..." --model="..." --file="..."

    The file is uploaded to the S3 bucket created during installation for
    digital twin files.

    """
    # NOTE: we will have to  pass these values inside the 'team' file if we want to let someone
    # other than the admin upload models.
    #
    try:
        config = preload_config(team, profile)
        bucket = config.config.get("templateBucketName", None)
        uuid_suffix = config.config.get("uuidSuffix", "")
        region = config.config.get("region", "")
        aws_profile = config.config.get("aws_profile", None)

        gen_file_url = None

        if not bucket:
            print(f"ERROR: no model upload bucket name found. Perhaps the installer didn't finish properly? Skipping.")
            exit(1)

        base_file=os.path.basename(file)
        gen_upload_filename=f"twin/{uuid_suffix}_{base_file}"

        if not os.path.exists(file):
            print(f"ERROR: file {file} not found")
            exit(1)

        gen_file_abs = os.path.abspath(file)

        print(f"Uploading {file}...")
        if aws_profile:
            boto3.setup_default_session(profile_name=aws_profile)

        s3 = boto3.client('s3', region)
        transfer = S3Transfer(s3)
        upload_args = {"ContentType": "application/zip",
                       "ACL": "bucket-owner-full-control"}

        if transfer:
            try:
                transfer.upload_file(filename=gen_file_abs,
                                     bucket=bucket,
                                     key=gen_upload_filename,
                                     callback=UploadProgress(file),
                                     extra_args=upload_args)
                gen_file_url = f"{s3.meta.endpoint_url}/{bucket}/{gen_upload_filename}"
            except Exception as e:
                print(f"ERROR uploading to S3: {str(e)}. Skipping.")
                # traceback.print_exc()
                exit(1)

        if not gen_file_url:
            print(f"Could not upload file {file} to S3.")
            exit(1)

        payload = {
            "project_name": project,
            "model": model,
            "glb_url": gen_file_url
        }

        url_params = urllib.parse.urlencode(payload)
        url = f"model?{url_params}"
        response = make_api_request('PUT', config, url)
        data = response.json()

        if response:
            print(f"\n\nSuccess. Model URL set to: {gen_file_url}")
        else:
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("List Status")
            table.add_column("Message")
            table.add_row(status, message)
            console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")


@twin.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--model", help="Model name", envvar="IOT_MODEL", required=True)
@click.option("--type", "--name", help="Data Type name", required=True)
@click.option("--position", "--data_position", help="DataType Twin position")
@click.option("--normal", "--data_normal", help="DataType Twin normal")
def data(team, profile, project, model, type, position, normal):
    """
    Update position and normal data for Digital 3D Twin
    \f
    Updates the position and normal data for a datatype to show on a digital twin.
    """

    try:
        config = preload_config(team, profile)
        payload = {
            "project_name": project,
            "model": model
        }
        if type:
            payload["name"] = type
        if position:
            payload["data_position"] = position
        if normal:
            payload["data_normal"] = normal


        url_params = urllib.parse.urlencode(payload)
        url = f"datatype?{url_params}"
        response = make_api_request('PUT', config, url)
        data = response.json()

        if response:
            model_id = data.get("id", "***")
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="bold green")
            table.add_column("DataType Update ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_column("Message")
            table.add_row(model_id, status, message)
        else:
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("Update Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")

