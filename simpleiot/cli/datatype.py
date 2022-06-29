#!/usr/bin/env python

# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
import click
from simpleiot.common.utils import make_api_request, show_detail, format_date
from simpleiot.common.config import *

import urllib, urllib.parse
from rich import print
from rich.console import Console
from rich.table import Table
import requests

console = Console()


@click.group()
def datatype():
    """Model DataType management"""


@datatype.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--model", help="Model name", envvar="IOT_MODEL", required=True)
@click.option("--name", help="DataType name", required=True)
@click.option("--desc", help="DataType Description", default="")
@click.option("--type", "--data_type", help="DataType type (i.e. integer, string, float)", default="integer")
@click.option("--units", help="DataType type units", default="")
@click.option("--show_on_twin", help="DataType shows on twin", type=bool, default=True)
@click.option("--data_position", help="DataType Twin position", default="")
@click.option("--data_normal", help="DataType Twin normal", default="")
@click.option("--label_template", help="DataType Twin label template", default="")
@click.option("--ranges", help="DataType value ranges JSON", default="")
@click.option("--rangefile", help="DataType value ranges JSON file", default="")
def add(team, profile, project, model, name, desc, type, units, show_on_twin,
        data_position, data_normal, label_template, ranges, rangefile):
    """Define a new Model DataType
    \f
    Examples:

    $ iot datatype add --name "..." --project "..." --model "..."

    To specify a default project, set the environment variable IOT_PROJECT to name of project.
    To specify a default model, set the environment variable IOT_MODEL to name of model.
    Doing so lets you skip the --project and --model flag.
    """
    try:
        config = preload_config(team, profile)

        payload = {
            "project_name": project,
            "model": model,
            "name": name
        }
        if desc:
            payload["desc"] = desc
        if type:
            payload["data_type"] = type
        if units:
            payload["units"] = units
        if show_on_twin:
            payload["show_on_twin"] = show_on_twin
        if data_position:
            payload["data_position"] = data_position
        if data_normal:
            payload["data_normal"] = data_normal
        if label_template:
            payload["label_template"] = label_template
        if rangefile:
            try:
                with open(rangefile, "r") as rf:
                    rangedata = rf.read()
                if rangedata:
                    payload["ranges"] = rangedata
            except:
                pass
        if ranges:
            payload["ranges"] = ranges

        response = make_api_request("POST", config, "datatype", json=payload)
        data = response.json()

        if response.status_code == requests.codes.ok:
            table = Table(show_header=True, header_style="green")
            table.add_column("DataType ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_column("Message")
            project_id = data.get("id", "***")
            status = data.get("status", "***")
            message = data.get("message", "***")
            table.add_row(project_id, status, message)
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


@datatype.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--model", help="Model name", envvar="IOT_MODEL", required=True)
@click.option("--name", help="DataType name", default=None)
@click.option("--id", help="Model ID", default=None)
@click.option("--full/--no-full", help="List Full Data", default=False)
def list(team, profile, project, model, name, id, full):
    """Return information on defined Datatypes
    \f
    Examples:
    \b
    $ iot datatype list --project "..." --model "..." --name "..."
    """
    try:
        config = preload_config(team, profile)

        multi = False

        if name:
            response = make_api_request("GET", config, f"datatype?project={project}&model={model}&name={name}")
        elif id:
            response = make_api_request("GET", config, f"datatype?project_name={project}&model={model}&id={id}")
        else:
            multi = True
            response = make_api_request("GET", config, f"datatype?project_name={project}&model={model}&all=true")

        data = response.json()
        if response.status_code == requests.codes.ok:
            if full and not multi:
                show_detail(console, "Datatype", data)
                return

            table = Table(show_header=True, header_style="green")
            table.add_column("DataType ID", style="dim", overflow="flow")
            table.add_column("Project")
            table.add_column("Model")
            table.add_column("Name")
            table.add_column("Type")
            table.add_column("Units")
            table.add_column("Date Created", justify="right")
            if multi:
                for d in data:
                    id = d.get("id", "***")
                    project = d.get("project", "***")
                    model = d.get("model", "***")
                    name = d.get("name", "***")
                    data_type = d.get("data_type", "***")
                    units = d.get("units", "***")
                    created = d.get("date_created", "***")
                    table.add_row(id, project, model, name, data_type, units, format_date(created))
            else:
                id = data.get("id", "***")
                project = data.get("project", "***")
                model = data.get("model", "***")
                name = data.get("name", "***")
                data_type = data.get("data_type", "***")
                units = data.get("units", "***")
                created = data.get("date_created", "***")
                table.add_row(id, project, model, name, data_type, units, format_date(created))
        else:
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("Model List Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")


@datatype.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--model", help="Model name", envvar="IOT_MODEL", required=True)
@click.option("--id", help="Model ID", default=None)
@click.option("--name", help="Datatype name", default=None)
@click.option("--desc", help="DataType description", default="")
@click.option("--type", "--data_type", help="DataType type (i.e. integer, string, float)", default="integer")
@click.option("--units", help="DataType type units", default="")
@click.option("--show_on_twin", help="DataType shows on twin", type=bool, default=False)
@click.option("--data_position", help="DataType Twin position", default="")
@click.option("--data_normal", help="DataType Twin normal", default="")
@click.option("--label_template", help="DataType Twin label template", default="")
@click.option("--ranges", help="DataType value ranges JSON", default="")
@click.option("--rangefile", help="DataType value ranges JSON file", default="")
def update(team, profile, project, model, id, name, desc, type, units,
           show_on_twin, data_position, data_normal, label_template,
           ranges, rangefile):
    """
    Update settings for a given Datatype
    \f
    Updates DeviceType attributes. NOTE: a DataType's project and model can not be modified.
    To change it, delete it then re-add with the new model.

    Examples:

    $ iot datatype update --name "..." --project "..."

    To specify a default project, set the environment variable IOT_PROJECT to name of project.
    To specify a default model, set the environment variable IOT_MODEL to name of model.
    Doing so lets you skip the --project and --project flags.
    """
    try:
        config = preload_config(team, profile)

        if not name and not id:
            print(f"Error: model 'name' or 'id' must be specified")
            exit(1)

        payload = {
            "project_name": project,
        }
        if model:
            payload["model"] = model
        if name:
            payload["name"] = name
        elif id:
            payload["id"] = id

        if desc:
            payload["desc"] = desc
        if type:
            payload["type"] = type
        if units:
            payload["units"] = units
        if show_on_twin:
            payload["show_on_twin"] = show_on_twin
        if data_position:
            payload["data_position"] = data_position
        if data_normal:
            payload["data_normal"] = data_normal
        if label_template:
            payload["label_template"] = label_template
        if rangefile:
            try:
                with open(rangefile, "r") as rf:
                    rangedata = rf.read()
                if rangedata:
                    payload["ranges"] = rangedata
            except:
                pass
        if ranges:
            payload["ranges"] = ranges

        url_params = urllib.parse.urlencode(payload)
        url = f"datatype?{url_params}"
        response = make_api_request("PUT", config, url)
        data = response.json()

        if response.status_code == requests.codes.ok:
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


@datatype.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--model", help="Model name", envvar="IOT_MODEL", required=True)
@click.option("--name", help="DataType name", default=None)
@click.option("--id", help="Project ID", default=None)
def delete(team, profile, project, model, name, id):
    """
    Delete an existing Datatype definition
    \f
    Examples:
    \b
    $ iot model delete --project "..." --model "..." --name "..."
    """
    try:
        config = preload_config(team, profile)

        response = None

        if name:
            response = make_api_request("DELETE", config, f"datatype?project_name={project}&model={model}&name={name}")
        elif id:
            response = make_api_request("DELETE", config, f"datatype?project_name={project}&model={model}&id={id}")

        data = response.json()

        if response.status_code == requests.codes.ok:
            id = data.get("id", "")
            status = data.get("status", "")
            message = data.get("message", "")
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
