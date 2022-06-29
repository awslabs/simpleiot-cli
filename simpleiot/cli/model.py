#!/usr/bin/env python

# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
import click
from simpleiot.common.utils import *
from simpleiot.common.config import *

import urllib, urllib.parse
from rich import print
from rich.console import Console
from rich.table import Table

##################################

console = Console()


@click.group()
def model():
    """Manage Models"""


@model.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--name", "--model", help="Model name", required=True)
@click.option("--desc", help="Model Description", default="")
@click.option("--revision", help="Model Revision", default="")
@click.option("--display_name", help="Model Display Name", default="")
@click.option("--display_order", help="Model Display Order", default="0")
@click.option("--image", help="Model Image URL", default="")
@click.option("--icon", help="Model Icon Image URL", default="")
@click.option("--require_position", help="Model Requires Position Data", is_flag=True)
@click.option("--type", help="Model Type", default="device")
@click.option("--security", help="Model Security", default="device")
@click.option("--storage", help="Model Storage", default="none")
@click.option("--protocol", help="Model Protocol", default="mqtt")
@click.option("--connection", help="Model Connection", default="direct")
@click.option("--ml", help="Model ML", default="none")
@click.option("--hw_version", help="Model Hardware Version")
@click.option('--template', help='Model Template Name to use', default="")
@click.option('--template_id', help='Model Template ID to use', default="")
def add(team, profile, project, name, desc, revision,
        display_name, display_order, image, icon, require_position,
        type, security, storage, protocol, connection, ml, hw_version,
        template, template_id):
    """
    Define a new device Model
    \f
    Examples:

    $ iot model add --name "..." --project "..."

    To specify a default project, set the environment variable IOT_PROJECT to name of project.
    Doing so lets you skip the --project flag.
    """
    try:
        config = preload_config(team, profile)

        payload = {
            "project_name": project,
            "name": name
        }
        if desc:
            payload["desc"] = desc
        if revision:
            payload["revision"] = revision
        if display_name:
            payload["display_name"] = display_name
        if display_order:
            payload["display_order"] = display_order
        if image:
            payload["image_url"] = image
        if icon:
            payload["icon_url"] = icon
        if require_position:
            payload["require_position"] = require_position
        if type:
            payload["type"] = type
        if protocol:
            payload["protocol"] = protocol
        if security:
            payload["security"] = security
        if storage:
            payload["storage"] = storage
        if connection:
            payload["connection"] = connection
        if ml:
            payload["ml"] = ml
        if hw_version:
            payload["hw_version"] = hw_version

        if template_id:
            payload['template_id'] = template_id
        else:
            if template:
                payload['template'] = template

        response = make_api_request("POST", config, "model", json=payload)
        data = response.json()

        if response:
            #
            # This creates the right local model cache directory, if needed
            #
            get_iot_model_dir(config.profile, project, name, create=True)

            table = Table(show_header=True, header_style="green")
            table.add_column("ID", style="dim", overflow="flow")
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
            table.add_column("Model Add Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as exc:
        print(f"ERROR: {str(exc)}")


@model.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--name", "--model", help="Model name", default=None)
@click.option("--id", help="Model ID", default=None)
@click.option("--full/--no-full", help="List Full Data", default=False)
def list(team, profile, project, name, id, full):
    """
    List defined Models and show details
    \f
    Examples:
    \b
    $ iot model list --project "..." --name "..."
    """
    try:
        config = preload_config(team, profile)

        multi = False

        if name:
            response = make_api_request("GET", config, f"model?project={project}&model={name}")
        elif id:
            response = make_api_request("GET", config, f"model?project_name={project}&model_id={id}")
        else:
            multi = True
            response = make_api_request("GET", config, f"model?project_name={project}&all=true")

        data = response.json()
        if response:
            if full and not multi:
                show_detail(console, "Model", data)
                return

            table = Table(show_header=True, header_style="green")
            table.add_column("Model ID", style="dim", overflow="flow")
            table.add_column("Project")
            table.add_column("Name")
            table.add_column("Type")
            table.add_column("Date Created", justify="right")
            if multi:
                for d in data:
                    id = d.get("id", "***")
                    project = d.get("project", "***")
                    model = d.get("model", "***")
                    model_type = d.get("type", "***")
                    created = d.get("date_created", "***")
                    table.add_row(id, project, model, model_type, format_date(created))
            else:
                id = data.get("id", "***")
                project = data.get("project", "***")
                model = data.get("model", "***")
                model_type = data.get("type", "***")
                created = data.get("date_created", "***")
                table.add_row(id, project, model, model_type, format_date(created))
        else:
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("Model List Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as exc:
        print(f"ERROR: {str(exc)}")


@model.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--id", help="Model ID")
@click.option("--name", "--model", help="Model name")
@click.option("--desc", help="Model Description")
@click.option("--revision", help="Model Revision")
@click.option("--display_name", help="Model Display Name")
@click.option("--display_order", help="Model Display Order")
@click.option("--image", help="Model Image URL")
@click.option("--icon", help="Model Icon Image URL")
@click.option("--require_position", help="Model Requires Position Data", is_flag=True)
@click.option("--type", help="Model Type")
@click.option("--security", help="Model Security")
@click.option("--storage", help="Model Storage")
@click.option("--protocol", help="Model Protocol")
@click.option("--connection", help="Model Connection")
@click.option("--ml", help="Model ML", default=None)
@click.option("--hw_version", help="Model Hardware Version")
def update(team, profile, project, id, name, desc, revision,
           display_name, display_order, image, icon, require_position,
           type, security, storage, protocol, connection, ml, hw_version):
    """
    Update Model attributes
    \f
    NOTE: a model's project can not be modified.
    To change it, delete it then re-add with the new project.

    Examples:

    $ iot model update --name "..." --project "..." --image

    To specify a default project, set the environment variable IOT_PROJECT to name of project.
    Doing so lets you skip the --project flag.
    """
    try:
        config = preload_config(team, profile)

        if not name and not id:
            print(f"Error: model 'name' or 'id' must be specified")
            exit(1)

        payload = {
            "project_name": project,
        }
        if name:
            payload["model"] = name
        elif id:
            payload["model_id"] = id

        if desc:
            payload["desc"] = desc
        if revision:
            payload["revision"] = revision
        if display_name:
            payload["display_name"] = display_name
        if display_order:
            payload["display_order"] = display_order
        if image:
            payload["image_url"] = image
        if icon:
            payload["icon_url"] = icon
        if require_position:
            payload["require_position"] = require_position
        if type:
            payload["type"] = type
        if protocol:
            payload["protocol"] = protocol
        if connection:
            payload["connection"] = connection
        if security:
            payload["security"] = security
        if storage:
            payload["storage"] = storage
        if ml:
            payload["ml"] = ml
        if hw_version:
            payload["hw_version"] = hw_version

        url_params = urllib.parse.urlencode(payload)
        url = f"model?{url_params}"
        response = make_api_request('PUT', config, url)
        data = response.json()

        if response:
            model_id = data.get("id", "***")
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="bold green")
            table.add_column("Model Update ID", style="dim", overflow="flow")
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
    except Exception as exc:
        print(f"ERROR: {str(exc)}")


@model.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT", required=True)
@click.option("--name", "--model", help="Model name", default=None)
@click.option("--id", help="Project ID", default=None)
def delete(team, profile, project, name, id):
    """
    Delete an existing Model and all related elements
    \f
    Examples:
    \b
    $ iot model delete --project "..." --name "..."
    """
    try:
        config = preload_config(team, profile)

        response = None

        if name:
            response = make_api_request("DELETE", config, f"model?project_name={project}&model={name}")
        elif id:
            response = make_api_request("DELETE", config, f"model?project_name={project}&model_id={id}")

        data = response.json()

        if response:
            delete_iot_model_dir(config.profile, project, name)
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
    except Exception as exc:
        print(f"ERROR: {str(exc)}")

