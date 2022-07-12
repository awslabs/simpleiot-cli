#!/usr/bin/env python

# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
import click
from simpleiot.common.utils import make_api_request, show_detail
from simpleiot.common.config import *

from rich import print
from rich.console import Console
from rich.table import Table
import requests

console = Console()

@click.group()
def data():
    """Data set and retrieve"""

@data.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--serial", help="Device Serial number", required=True)
@click.option("--name", "--type", help="Data name", default='')
@click.option("--desc", help="Data Description", default='')
@click.option("--value", help="Data value", default='')
@click.option("--data", help="Data series (name=value,name=value,...)", default='')
@click.option("--position", help="Data position (lat, long, alt)", default='')
@click.option("--dimension", help="Data dimension", default='')
def set(team, profile, project, serial, name, desc, value, data, position, dimension):
    """Set value for a given data element
    \f
    Examples:

    $ iot data set --project "..." --serial "..." --name "..." --value "..."
    $ iot data set --project "..." --serial "..." --data="name=value,name-value,..." ...

    To specify a default project, set the environment variable IOT_PROJECT to name of project.
    Doing so lets you skip the --project flag.

    To specify a data series (i.e. multiple settings at the same time, use the "--data"
    parameter. Values provided with the --name/--value parameter are then ignored.
    """
    try:
        config = preload_config(team, profile)

        if data:
            dataparams = {}
            datalist = data.split(",")
            for one in datalist:
                kvlist = one.split("=")
                try:
                    if len(kvlist) == 2:
                        n = kvlist[0].strip()
                        v = kvlist[1].strip()
                        dataparams[n] = v
                except Exception as e:
                    print(f"Invalid data parameter in [ {kvlist} ]. Skipping.")
                    pass
                data_str = ','.join('{}={}'.format(k,v) for k,v in dataparams.items())
            payload = {
                "project": project,
                "serial": serial,
                "data": data_str
            }
        else:
            payload = {
                "project": project,
                "serial": serial,
                "name": name,
                "value": value
            }

        if desc:
            payload["desc"] = desc
        if position:
            payload["position"] = position
        if dimension:
            payload["dimension"] = dimension

        response = make_api_request("POST", config, "data", json=payload)

        data = response.json()
        if response.status_code == requests.codes.ok:
            table = Table(show_header=True, header_style="green")
            table.add_column("Data ID", style="dim", overflow="flow")
            table.add_column("Project")
            table.add_column("Serial")
            table.add_column("Name")
            table.add_column("Value")
            ret_data = data.get("data", None)
            for item in ret_data:
                project_id = item.get("id", "***")
                serial = item.get("serial", "***")
                name = item.get("name", "***")
                value = item.get("value", "***")
                project_name = item.get("project", "***")
                table.add_row(project_id, project_name, serial, name, value)

        else:
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("Data Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")


@data.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--serial", help="Serial number", required=True)
@click.option("--name", "--type", help="Data name", default=None)
@click.option("--full/--no-full", help="List Full Data", default=False)
def get(team, profile, project, serial, name, full):
    """Return last known value for a given data element
    \f
    Examples:

    $ iot data get --project "..." --serial "..." --name "..."
    """
    try:
        config = preload_config(team, profile)

        multi = False

        if not name:
            print("Missing data name")
            return

        response = make_api_request("GET", config, f"data?project={project}&serial={serial}&name={name}")

        data = response.json()
        if response.status_code == requests.codes.ok:
            if full and not multi:
                show_detail(console, "Data", data)
                return

            table = Table(show_header=True, header_style="green")
            table.add_column("Data ID", style="dim", overflow="flow")
            table.add_column("Project")
            table.add_column("Serial")
            table.add_column("Name")
            table.add_column("Value")
            table.add_column("Timestamp", justify="right")
            project_id = data.get("id", "***")
            serial = data.get("serial", "***")
            name = data.get("name", "***")
            value = data.get("value", "***")
            timestamp = data.get("timestamp", "***")
            table.add_row(project_id, project, serial, name, value, timestamp)
        else:
            status = data.get("status", "")
            message = data.get("message", "")
            table = Table(show_header=True, header_style="red")
            table.add_column("Data List Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")


@data.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--serial", help="Serial number", required=True)
@click.option("--name", help="Data name", default=None)
def delete(team, profile, project, serial, name):
    """Delete a data item already in the system
    \f
    Examples:

    $ iot data delete --project "..." --serial "..." --name "..."
    """
    try:
        config = preload_config(team, profile)

        response = None

        if name:
            response = make_api_request("DELETE", config, f"data?project_name={project}&serial={serial}&name={name}")

        data = response.json()

        if response.status_code == requests.codes.ok:
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
