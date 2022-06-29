#!/usr/bin/env python

# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
import click
import requests
from simpleiot.common.utils import make_api_request, show_detail
from simpleiot.common.config import *
from urllib.parse import unquote
from rich import print
from rich.console import Console
from rich.table import Table
from pathlib import Path
import uuid


console = Console()

@click.group()
def update():
    """OTA Firmware Updates"""

@update.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--model", help="Model Name", default='')
@click.option("--serial", help="Device Serial number", default='')
@click.option("--file", help="Payload file", required=True)
@click.option("--name", "--type", help="Data name", default='')
@click.option("--desc", help="Data Description", default='')
@click.option("--version", help="Update version", required=True)
@click.option("--release_note", help="Inline release notes", default='')
@click.option("--user_data", help="Inline extra user-data", default='')
def upload(team, profile, project, model, serial, file, name, desc, version,
           release_note, user_data):
    """
    Upload binary file for staging firmware update
    \f
    Use this to upload firmware for distribution. Sending updates is a two-step
    process. First is to upload the payload file. Then to submit an update to a list of
    target devices.

    The upload part itself has three parts:
    1) Send a call with the name of payload file.
    2) Get back a pre-signed URL for uploading to S3 using a PUT call.
    3) Call again when upload is finished to indicate upload is done.

    This command encapsulates all three steps.

    The step where the update is sent is captured in a different call.
    """
    try:
        config = preload_config(team, profile)

        raw_url = None
        url = None
        data = None
        firmware_id = None

        upload_file = Path(file)
        if not upload_file.is_file():
            print(f"ERROR: file {file} does not exist")
            exit(1)

        payload = {
            "project": project,
            "file": file,
            "item": "upload"
        }
        if serial:
            payload["serial"] = serial
        elif model:
            payload["model"] = model

        if version:
            payload["version"] = version
        if name:
            payload["name"] = name
        if desc:
            payload["desc"] = desc
        if release_note:
            payload["release_note"] = release_note
        if user_data:
            payload["user_data"] = user_data

        response = make_api_request("POST", config, "update", json=payload)
        data = response.json()

        # This returns a URL that is urlencoded. We need to urldecode it to get the pre-signed URL
        # where we upload the file. But in the third step, we need to return the same urlencoded
        # pre-signed URL, so we need to keep it around.
        #
        if response:
            firmware_id = data.get('firmware_id', None)
            raw_url = data.get('url', None)
            if raw_url:
                url = unquote(raw_url)

            # The URL returned is a pre-signed URL for use with a PUT call.

            if firmware_id and url:
                headers = {'Content-type': 'application/x-binary', 'Slug': file}
                response = requests.put(url, data=open(file, 'rb')) #, headers=headers)
                if response:
                    second_payload = {
                        "project": project,
                        "item": "payload",
                        "firmware_id": firmware_id,
                        "url": raw_url
                    }
                    response = make_api_request("POST", config, "update", json=second_payload)
                    data = response.json()
                    if response:
                        firmware_id = data['firmware_id']

                        table = Table(show_header=True, header_style="green")
                        table.add_column("Project")
                        if serial:
                            table.add_column("Serial")
                        elif model:
                            table.add_column("Model")
                        table.add_column("File")
                        table.add_column("Upload ID", min_width=32, overflow="flow")
                        if serial:
                            table.add_row(project, serial, file, firmware_id)
                        elif model:
                            table.add_row(project, model, file, firmware_id)

                        console.print(table)
                    else:
                        print(f"ERROR: could not finalize upload. Please remove and try again: {str(response.text)}")
            else:
                print("ERROR: invalid data returned from API. Make sure you remove the Firmware record.")
                exit(1)
        else:
            print(f"Error requesting a pre-signed URL to upload firmware: {response.text}")

    except Exception as e:
        print(f"ERROR: {str(e)}")


@update.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--name", help="Session name", default="")
@click.option("--id", "--upload_id", help="Upload ID (from 'upload' command", required=True)
@click.option("--serial", help="Device serial number", default=None)
@click.option("--model", help="Model name", default=None)
def push(team, profile, project, name, id, serial, model):
    """
    Push firmware update to devices
    \f
    Examples:
    \b
    $ iot update push --project "..." --serials "..."
    """
    try:
        config = preload_config(team, profile)

        multi = False
        data = None

        if not (serial or model):
            print("ERROR: need to specify either comma-separated serial numbers or model name for a target device")
            return

        # Using this to verify that it's the right format
        id_check = uuid.UUID(id)

        payload = {
            "project": project,
            "firmware_id": id,
            "item": "session"
        }

        if serial:
            payload["serial"] = serial
        elif model:
                payload["model"] = model

        response = make_api_request("POST", config, "update", json=payload)
        data = response.json()
        if response:
            table = Table(show_header=True, header_style="green")
            table.add_column("Upload ID", style="dim", min_width=32, overflow="flow")
            table.add_column("Project")
            if serial:
                table.add_column("Serial")
            elif model:
                table.add_column("Model")
            table.add_column("Status")

            if serial:
                table.add_row(id, project, serial, "OK")
            if model:
                table.add_row(id, project, model, "OK")
        else:
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("Push Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        traceback.print_exc()

@update.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT")
@click.option("--version", help="Version number", default="")
@click.option("--id", "--firmware_id", help="Upload ID (from 'upload' command")
@click.option("--serial", "--device", help="Device serial number", default=None)
@click.option("--model", help="Model name", default=None)
@click.option("--full/--no-full", help="List Full Data", default=False)
def list(team, profile, project, version, id, serial, model, full):
    """
    List firmware uploaded and ready to be pushed
    """
    try:
        config = preload_config(team, profile)

        multi = False
        data = None

        payload = {
            "item": "upload"
        }

        if id:
            payload["id"] = id
        if project:
            payload["project"] = project
        if serial:
            payload["serial"] = serial
        if model:
            payload["model"] = model

        if not (id or project or serial or model):
            print("ERROR: need to specify one of '--firmware' or '--project and --serial' or '--model' ")
            return

        response = make_api_request("GET", config, "update", params=payload)
        data = response.json()

        if response:
            if full:
                one = data[0]
                show_detail(console, "Update", one)
                return

            table = Table(show_header=True, header_style="green")
            table.add_column("Firmware ID", style="dim", min_width=32, overflow="flow")
            table.add_column("Name", max_width=15)
            table.add_column("Model")
            table.add_column("Serial")
            table.add_column("State")
            table.add_column("Version")

            for one in data:
                update_id = one.get("id", "")
                update_name = one.get("name", "")
                update_serial = one.get("serial", "***")
                update_model = one.get("model", "")
                update_url = one.get("url", "")
                update_state = one.get("state", "")
                update_version = one.get("version", "")
                table.add_row(update_id, update_name, update_model, update_serial, update_state, update_version)
        else:
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("List Update Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")


@update.command()
@common_cli_params
@click.option("--id", "--firmware_id", help="Upload ID (from 'upload' command")
def delete(team, profile, id):
    """
    Delete an existing OTA update file from the staging site
    \f
    Examples:
    \b
    $ iot update delete --id "..."
    """
    try:
        config = preload_config(team, profile)
        response = None

        if name:
            response = make_api_request("DELETE", config, f"update?firmware_id={id}")

        data = response.json()

        if response:
            id = data.get("id", "***")
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="bold green")
            table.add_column("Deleted ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_column("Message")
            table.add_row(id, status, message)
        else:
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("Delete Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")
