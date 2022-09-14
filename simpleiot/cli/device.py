#!/usr/bin/env python

# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
import click
import json
import time
from simpleiot.common.utils import *
from simpleiot.common.config import *
import signal
import sys

import urllib, urllib.parse
from rich import print
from rich.console import Console
from rich.table import Table
import requests

console = Console()


@click.group()
def device():
    """Device provisioning"""


@device.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--model", help="Device model", envvar="IOT_MODEL", required=True)
@click.option("--serial", help="Device Serial", required=True)
@click.option("--name", help="Device name", default="")
@click.option("--desc", help="Device Description", default="")
@click.option("--position", help="Device Position", default="")
@click.option("--latitude", help="Device Latitude", type=float, default=None)
@click.option("--longitude", help="Device Longitude", type=float, default=None)
@click.option("--altitude", help="Device Altitude", type=float, default=None)
@click.option("--status", help="Device Status", default=None)
@click.option("--error", help="Device Error Message", default=None)
@click.option("--arduino", help="Name of arduino project to generate", default=None)
@click.option("--wifi_ssid", "--ssid", help="Wifi SSID name", envvar="IOT_WIFI_SSID")
@click.option("--wifi_password", "--password", help="Wifi Password", envvar="IOT_WIFI_PASSWORD")

def add(team, profile, project, model, serial, name, desc,
        position, latitude, longitude, altitude,
        status, error, arduino, wifi_ssid, wifi_password):
    """
    Provision a single device
    \f
    Adds a new Device to the system. Project, Model, and Serial Number are required.
    Examples:
    \b
    $ iot device add --project "..." --model "..." --serial "..." ...

    To specify a default project, set the environment variable IOT_PROJECT to name of project.
    To specify a default model, set the environment variable IOT_MODEL to name of model.
    Doing so lets you skip the --project and --model flags.
    """
    try:
        config = preload_config(team, profile)

        payload = {
            "project_name": project,
            "model": model,
            "serial": serial
        }
        qr_data = json.dumps(payload)

        if name:
            payload["name"] = name
        if desc:
            payload["desc"] = desc
        if position:
            payload["position"] = position
        if latitude:
            payload["latitude"] = latitude
        if longitude:
            payload["longitude"] = longitude
        if altitude:
            payload["altitude"] = altitude
        if status:
            payload["status"] = status
        if error:
            payload["error"] = error

        response = make_api_request("POST", config, "device", json=payload)

        data = response.json()
        if response.status_code == requests.codes.ok:
            #
            # This creates the right local device cache directory, if needed
            #
            device_dir = get_iot_device_dir(config.team, project, model, serial, create=True)

            ca_data = data.get("ca_pem", None)
            if ca_data:
                write_device_cert_file(device_dir, serial, "rootca", ca_data)
            cert_data = data.get("cert_pem", None)
            write_device_cert_file(device_dir, serial, "cert", cert_data)
            public_key = data.get("public_key", None)
            write_device_cert_file(device_dir, serial, "public", public_key)
            private_key = data.get("private_key", None)
            write_device_cert_file(device_dir, serial, "private", private_key)

            table = Table(show_header=True, header_style="green")
            table.add_column("Device ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_column("Message")
            device_id = data.get("id", "***")
            status = data.get("status", "***")
            message = data.get("message", "***")
            table.add_row(device_id, status, message)
        else:
            data = response.json()
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("List Status")
            table.add_column("Message")
            table.add_row(status, message)
        console.print(table)

        # iot_endpoint = config.api_endpoint
        # print(f"Certificate directory: {device_dir}")
        # print(f"IOT Endpoint: {iot_endpoint}")

        ## NOTE: this could be a generic output with device settings, so it invokes the toolchainbase class type
        # and lets *THAT* do the code generation. This way, each toolchain can auto generate its own skeleton
        # code and spit it out the way it's meant to.
        # NOTE 2: The firmware build/flash command should accept a folder instead of a zip file, so it can
        # compile and flash from an existing directory.
        #

        # If the arduino value is set, we will generate a full arduino project with a directory defined as the arduino
        # name, an .ino file that includes the proper files and sets the settings, the certs and wifi files
        # and a skeleton project that includes code to set the Datatypes defined for the project. All you have to do
        # is go wire up the sensors to the right variables and it's good to go.
        #
        if arduino:
            pass

        #print("NOTE: If this is a gateway, be sure to finish GG set-up from the device itself.")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        traceback.print_exc()

def write_device_cert_file(base, serial, suffix, data):
    try:
        if data:
            filename = f"{serial}_{suffix}.pem"
            file = os.path.join(base, filename)
            with open(file, "w") as out:
                out.write(data + '\n')
    except Exception as e:
        print(
            f"ERROR: unable to save device data for {serial} to {base} directory. Please delete device, fix problem, and try again")

@device.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", default=None)
@click.option("--model", help="Device model", envvar="IOT_MODEL", default=None)
@click.option("--serial", help="Device Serial", envvar="IOT_DEVICE_SERIAL", default=None)
@click.option("--id", help="Device ID", default=None)
@click.option("--location", help="Location Name", default=None)
@click.option("--location_id", help="Location ID", default=None)
@click.option("--full/--no-full", help="List Full Data", default=False)
def list(team, profile, project, model, serial, id, location, location_id, full):
    """
    Show information on one or more devices
    \f
    Lists information on device instances already in system.
    Examples:
    \b
    $ iot device list --project "..." ...
    """
    try:
        config = preload_config(team, profile)

        multi = False

        # If there's a serial, we explicitly show the one device
        if location:
            multi = True
            response = make_api_request("GET", config, f"device?project_name={project}&location={location}")
        elif location_id:
            response = make_api_request("GET", config, f"device?project_name={project}&location_id={location_id}")
        elif project and serial:
            response = make_api_request("GET", config, f"device?project_name={project}&serial={serial}")
        # Or a GUID
        elif project and id:
            response = make_api_request("GET", config, f"device?project_name={project}&id={id}")
        # If just a model, we show all devices of that model
        elif project and model:
            multi = True
            response = make_api_request("GET", config, f"device?project_name={project}&model={model}")
        # Otherwise, all devices for this project
        elif project:
            multi = True
            response = make_api_request("GET", config, f"device?project_name={project}&all=true")
        else:
            print("ERROR: insufficient paramters. Need at least project or location")
            exit(1)

        data = response.json()
        if response.status_code == requests.codes.ok:
            if full and not multi:
                show_detail(console, "Device", data)
                return

            table = Table(show_header=True, header_style="bold green")
            table.add_column("Device ID", style="dim", overflow="flow")
            if location or location_id:
                table.add_column("Location")
            else:
                table.add_column("Model")

            table.add_column("Serial")
            table.add_column("Name")
            table.add_column("Date Created", justify="right")
            if multi:
                for d in data:
                    id = d.get("id", "***")
                    model = d.get("model", "***")
                    serial = d.get("serial", "***")
                    name = d.get("name", "***")
                    created = d.get("date_created", "***")

                    if location or location_id:
                        table.add_row(id, location, serial, name, format_date(created))
                    else:
                        table.add_row(id, model, serial, name, format_date(created))
            else:
                id = data.get("id", "***")
                model = data.get("model", "***")
                serial = data.get("serial", "***")
                name = data.get("name", "***")
                created = data.get("date_created", "***")
                table.add_row(id, model, serial, name, format_date(created))
        else:
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("Device Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")

@device.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--model", help="Device model", envvar="IOT_MODEL", default=None)
@click.option("--serial", help="Device Serial", envvar="IOT_DEVICE_SERIAL", default=None)
@click.option("--id", help="Device ID", default=None)
@click.option("--output", help="Write output config file to this file", default='iotconfig.json')
def getconfig(team, profile, project, model, serial, id, output):
    """
    Generate iotconfig.json file for use in SimpleIOT clients
    \f
    Examples:
    \b
    $ iot device getconfig --project "..." ...
    """
    config = preload_config(team, profile)

    # # If there's a serial, we explicitly show the one device
    # if serial:
    #     response = make_api_request('GET', config, f"device?project_name={project}&serial={serial}")
    # # Or a GUID
    # elif id:
    #     response = make_api_request('GET', config, f"device?project_name={project}&id={id}")
    # # If just a model, we show all devices of that model
    # elif model:
    #     multi = True
    #     response = make_api_request('GET', config, f"device?project_name={project}&model={model}")
    # # Otherwise, all devices for this project
    # else:
    #     multi = True
    #     response = make_api_request('GET', config, f"device?project_name={project}&all=true")
    #
    # data = response.json()
    #
    # if response:
    #     if full and not multi:
    #         show_detail(console, "Device", data)
    #         return
    #
    #     table = Table(show_header=True, header_style="bold green")
    #     table.add_column("Device ID", style="dim", overflow="flow")
    #     table.add_column("Project")
    #     table.add_column("Model")
    #     table.add_column("Serial")
    #     table.add_column("Name")
    #     table.add_column("Date Created", justify="right")
    #     if multi:
    #         for d in data:
    #             id = d['id']
    #             project = d['project']
    #             model = d['model']
    #             serial = d['serial']
    #             name = d.get('name', "")
    #             created = d['date_created']
    #             table.add_row(id, project, model, serial, name, created)
    #     else:
    #         id = data['id']
    #         project = data['project']
    #         model = data['model']
    #         serial = data['serial']
    #         name = data.get('name', "")
    #         created = data['date_created']
    #         table.add_row(id, project, model, serial, name, created)
    # else:
    #     status = data.get('status', "")
    #     message = data.get('message', "")
    #     table = Table(show_header=True, header_style="red")
    #     table.add_column("Device Status")
    #     table.add_column("Message")
    #     table.add_row(status, message)
    #
    # console.print(table)


@device.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--id", help="Device ID", default=None)
@click.option("--serial", help="Device Serial", required=True)
@click.option("--name", help="Model name", required=True)
@click.option("--desc", help="Model Description", default="")
@click.option("--position", help="Model Position", default="")
@click.option("--latitude", help="Device Latitude", type=float, default=None)
@click.option("--longitude", help="Device Longitude", type=float, default=None)
@click.option("--altitude", help="Device Altitude", type=float, default=None)
@click.option("--status", help="Device Status", default=None)
@click.option("--error", help="Device Error Message", default=None)
def update(team, profile, project, id, serial, name, desc, position,
           latitude, longitude, altitude, status,
           error):
    """
    Update individual device meta-data settings
    \f
    Updates Device attributes. NOTE: a device's project or serial can not be modified.
    To change it, delete it then re-add.

    Examples:
    \b
    $ iot device update --name "..." --project "..." --image

    To specify a default project, set the environment variable IOT_PROJECT to name of project.
    Doing so lets you skip the --project flag.
    """
    try:
        config = preload_config(team, profile)

        if not serial and not id:
            print(f"Error: device 'serial' or 'id' must be specified")
            exit(1)

        payload = {
            "project_name": project,
        }
        if serial:
            payload["serial"] = serial
        elif id:
            payload["id"] = id

        if name:
            payload["name"] = name
        if desc:
            payload["desc"] = desc
        if position:
            payload["position"] = position
        if latitude:
            payload["latitude"] = latitude
        if longitude:
            payload["longitude"] = longitude
        if altitude:
            payload["altitude"] = altitude
        if status:
            payload["status"] = status
        if error:
            payload["error"] = error

        url_params = urllib.parse.urlencode(payload)
        url = f"devicel?{url_params}"
        response = make_api_request('PUT', config, url)
        data = response.json()
        if response.status_code == requests.codes.ok:
            model_id = data.get("id", "***")
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="green")
            table.add_column("Device Update ID", style="dim", overflow="flow")
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


@device.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--serial", help="Device serial", default=None)
@click.option("--id", help="Device ID", default=None)
def delete(team, profile, project, serial, id):
    """
    Remove and de-provision an existing device instance
    \f
    Deletes a device already in the system.
    Examples:

    $ iot device delete --project "..." --serial "..."
    $ iot device delete --project "..." --id "..."
    """
    try:
        config = preload_config(team, profile)

        response = None

        if serial:
            response = make_api_request("DELETE", config, f"device?project_name={project}&serial={serial}")
        elif id:
            response = make_api_request("DELETE", config, f"device?project_name={project}&id={id}")

        data = response.json()
        if response.status_code == requests.codes.ok:
            # project = data.get("project", None)
            model = data.get("model", None)
            if model:
                delete_iot_device_dir(config.profile, project, model, serial)
            else:
                print("API Error: did not return device model. Could not delete local device directory")

            id = data.get("id", "***")
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="green")
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

# Attach/detach associates a node device with a gateway. We verify that the target is
# a gateway, then create an association both in the database as well as
# in Greengrass. This allows each node device to directly connect to the gateway
# if used for device discovery.
#
# Detach goes the other way, removes the attachment and removes the device from the
# Greengrass group.
#
# NOTE that devices can only be attached/detached to devices in the same project.
#
@device.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--serial", help="Device serial", default=None)
@click.option("--to", "--gateway", help="Gateway serial", default=None)
@click.option("--from_id", help="End Device ID", default=None)
@click.option("--to_id", help="Gateway Device ID", default=None)
def attach(team, profile, project, serial, to, from_id, to_id):
    """
    Attach and end-node device to a gateway
    \f
    Examples:

    $ iot device attach --project "..." --serial "..." --to "..."
    $ iot device attach --project "..." --id "..." --to "..."
    """
    try:
        config = preload_config(team, profile)

        response = None
        query = None

        if serial and to:
            query = f"device?op=attach&project={project}&device={serial}&gateway={to}"
        elif serial and to_id:
            query = f"device?op=attach&project={project}&device_id={from_id}&gateway_id={to_id}"
        elif from_id and to:
            query = f"device?op=attach&project={project}&device_id={from_id}&gateway={to}"
        elif from_id and to_id:
            query = f"device?op=attach&project={project}&device_id={from_id}&gateway_id={to_id}"

        if not query:
            print("ERROR: device and gateway need to be specified")
            exit(1)

        response = make_api_request("PUT", config, query)
        data = response.json()
        if response.status_code == requests.codes.ok:
            id = data.get("id", "***")
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="green")
            table.add_column("Attached ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_column("Message")
            table.add_row(id, status, message)
        else:
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("Attach Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")

@device.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--serial", help="Device serial", default=None)
@click.option("--to", "--gateway", help="Gateway serial", default=None)
@click.option("--from_id", help="End Device ID", default=None)
@click.option("--to_id", help="Gateway Device ID", default=None)
def detach(team, profile, project, serial, to, from_id, to_id):
    """
    Detach an end-device from a gateway
    \f
    Examples:

    $ iot device detach --project "..." --serial "..." --to "..."
    $ iot device detach --project "..." --id "..." --to "..."
    """
    try:
        config = preload_config(team, profile)

        response = None
        query = None

        if serial and to:
            query = f"device?op=detach&project={project}&device={serial}&gateway={to}"
        elif serial and to_id:
            query = f"device?op=detach&project={project}&device_id={from_id}&gateway_id={to_id}"
        elif from_id and to:
            query = f"device?op=detach&project={project}&device_id={from_id}&gateway={to}"
        elif from_id and to_id:
            query = f"device?op=detach&project={project}&device_id={from_id}&gateway_id={to_id}"

        if not query:
            print("ERROR: device and gateway need to be specified")
            exit(1)

        response = make_api_request("PUT", config, query)
        data = response.json()

        if response.status_code == requests.codes.ok:
            id = data.get("id", "***")
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="green")
            table.add_column("Detached Device ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_column("Message")
            table.add_row(id, status, message)
        else:
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("Detach Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")


# Place/remove associates a device with a pre-defined location. Locations have to
# be created ahead of time using "iot location add" and given a unique name.
#
# Remove goes the other way, removes the location attachment.
#
# NOTE that devices can only be placed/unplaced in the same project.
#
@device.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--serial", "--device", help="Device serial", default=None)
@click.option("--at", "--location", help="Location name", default=None)
@click.option("--device_id", help="Device ID", default=None)
@click.option("--location_id", help="Location ID", default=None)
def place(team, profile, project, serial, at, location_id, device_id):
    """Place an end-device at a known location
    \f
    Examples:

    $ iot device place --project "..." --serial "..." --at "..."
    """
    try:
        config = preload_config(team, profile)

        response = None
        query = None

        if serial and at:
            query = f"device?op=place&project={project}&device={serial}&location={at}"
        elif serial and location_id:
            query = f"device?op=place&project={project}&device={device}&location_id={location_id}"
        elif device_id and at:
            query = f"device?op=place&project={project}&device_id={device_id}&gateway={at}"
        elif device_id and location_id:
            query = f"device?op=place&project={project}&device_id={device_id}&location_id={location_id}"

        if not query:
            print("ERROR: device and location need to be specified")
            exit(1)

        response = make_api_request("PUT", config, query)
        data = response.json()
        if response.status_code == requests.codes.ok:
            status = data.get("status", "***")
            device_id = data.get("device", "***")
            location_id = data.get("location", "***")
            table = Table(show_header=True, header_style="green")
            table.add_column("Device ID", style="dim", overflow="flow")
            table.add_column("Location ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_row(device_id, location_id, status)
        else:
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("Place Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")

@device.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", default=None)
@click.option("--serial", "--device", help="Device serial", default=None)
@click.option("--id", help="Device ID", default=None)
def remove(team, profile, project, serial, id):
    """
    Remove an end-device from a location
    \f
    Examples:

    $ iot device remove --project "..." --serial "..."
    """
    try:
        config = preload_config(team, profile)

        response = None
        query = None

        if project and serial:
            response = make_api_request("PUT", config, f"device?op=remove&project={project}&device={serial}")
        elif id:
            response = make_api_request("PUT", config, f"device?op=remove&device_id={id}")
        else:
            print("ERROR: Device --project and --serial OR --id has to be specified")
            exit(1)

        data = response.json()

        if response.status_code == requests.codes.ok:
            device = data.get("device", "***")
            location = data.get("location", "***")
            status = data.get("status", "***")
            table = Table(show_header=True, header_style="green")
            table.add_column("Device ID", style="dim", overflow="flow")
            table.add_column("Location ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_row(device, location, status)
        else:
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("Place Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")


def on_error_callback(error):
    table = Table(show_header=True, header_style="red")
    table.add_column("Error Message", style="bold", overflow="flow")
    table.add_row(f"[red]{error}[/red]")
    console.print(table)


def on_data_callback(topic, payload, show_raw, stop_after_one):
    name = payload.get("name", "**no-name**")
    value = payload.get("value", "**no-name**")
    #print(f"{topic}: {name} = {value}")

    if show_raw:
        payload_str = json.dumps(payload, indent=2)
        print(payload_str)
    else:
        table = Table(show_header=True, header_style="green")
        table.add_column("Data", style="bold", overflow="flow")
        table.add_column("Value", style="bold", overflow="flow")
        print_args = [f"[magenta]{name}[/magenta]", f"[yellow]{value}[/yellow]"]
        geo_lat = payload.get("geo_lat", None)
        geo_lng = payload.get("geo_lng", None)
        geo_alt = payload.get("geo_alt", None)
        if geo_lat:
            table.add_column("GPS Lat", style="bold", overflow="flow")
            print_args.append(f"[cyan]{geo_lat}[/cyan]")
        if geo_lng:
            table.add_column("GPS Lng", style="bold", overflow="flow")
            print_args.append(f"[cyan]{geo_lng}[/cyan]")
        if geo_alt:
            table.add_column("GPS Alt", style="bold", overflow="flow")
            print_args.append(f"[cyan]{geo_alt}[/cyan]")

        table.add_row(*print_args)
        console.print(table)

    # If we're told to stop after one round, we tell the callback to exit by returning a False
    #
    if stop_after_one:
        return False
    else:
        return True

def _control_c_handler(sig, frame):
    sys.exit(0)

#
# Device monitor lets you watch traffic going across the device. If invoked by itself
# it runs interactively and shows each command until user hits Control-C.
# If --raw is specified, we display only the JSON retrieved.
# If --stop is specified, we stop after only showing a single incoming update. This and --raw can then
# be used for unit-testing end-to-end message transmission.
#
@device.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--model", help="Model name", envvar="IOT_MODEL", required=True)
@click.option("--serial", "--device", help="Device serial", required=True)
@click.option('--raw/--no-raw', help='Show raw data', default=False)
@click.option('--stop/--no-stop', help='Stop after receiving a single item', default=False)
def monitor(team, profile, project, model, serial, raw, stop):
    """
    Monitor device traffic for a given device. We use the device certs and topic
    to watch what is going on with a single device.
    \f
    Examples:

    $ iot device monitor --project "..." --serial "..."

    To stop the monitoring, hit Control-C to interrupt.
    """
    try:
        config = preload_config(team, profile)

        topic = f"simpleiot_v1/app/monitor/{project}/{model}/{serial}/#"
        subscribe_to_mqtt_topic(config.team, project, model, serial, topic, raw, stop, on_data_callback, on_error_callback)

        if not raw:
            print(f"-- Watching data for device [{serial}]")

        if not stop:
            print(f"-- To stop, press Control-C.\n")

        loop_count = 0
        signal.signal(signal.SIGINT, _control_c_handler)
        while True:
            loop_count += 1
            time.sleep(1)
    except Exception as e:
        print(f"ERROR: {str(e)}")

