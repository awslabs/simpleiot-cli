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

console = Console()

@click.group()
def project():
    """Project management"""

@project.command()
@common_cli_params
@click.option('--name', help='Project name', required=True)
@click.option('--desc', help='Project Description', default="")
@click.option('--template', help='Template Name to use', default="")
@click.option('--template_id', help='Template ID to use', default="")
def add(team, profile, name, desc, template, template_id):
    """
    Define a new Project
    \f
    Example:

    $ iot project add --name "..."
    """
    try:
        config = preload_config(team, profile)

        payload = {
            "project_name": name,
            "desc": desc
        }

        if template_id:
            payload['template_id'] = template_id
        else:
            if template:
                payload['template_name'] = template

        response = make_api_request('POST', config, 'project', json=payload)
        if response:
            data = response.json()
            #
            # This creates the right local directory, if needed
            #
            get_iot_project_dir(config.profile, name, create=True)

            table = Table(show_header=True, header_style="bold green")
            table.add_column("ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_column("Message")
            project_id = data.get("id", "")
            status = data.get("status", "ok")
            message = data.get("message", "")
            table.add_row(project_id, status, message)
            console.print(table)
    except Exception as exc:
        print(f"ERROR: {str(exc)}")


@project.command()
@common_cli_params
@click.option('--name', '--project', help='Project name', default=None)
@click.option('--id', help='Project ID', default=None)
@click.option('--full/--no-full', help='List Full Data', default=False)
def list(team, profile, name, id, full):
    """
    List defined Projects and show details
    \f
    Examples:

    $ iot project list --name "..."
    """
    try:
        config = preload_config(team, profile)
        multi = False

        if name:
            response = make_api_request('GET', config, f"project?project_name={name}")
        elif id:
            response = make_api_request('GET', config, f"project?project_id={id}")
        else:
            multi = True
            response = make_api_request('GET', config, f"project?all=true")

        data = response.json()

        if response:
            if full and not multi:
                show_detail(console, "Project", data)
                return

            table = Table(show_header=True, header_style="bold green")
            table.add_column("ID", style="dim", overflow="flow")
            table.add_column("Name")
            table.add_column("Date Created", justify="right")
            #print(f"RESULT: Type: {type(data)} - {data}")
            if multi:
                for d in data:
                    table.add_row(d['id'], d['name'], format_date(d['date_created']))
            else:
                table.add_row(data['id'], data['name'], format_date(data['date_created']))
        else:
            status = data.get('status', "")
            message = data.get('message', "")
            table = Table(show_header=True, header_style="red")
            table.add_column("Project List Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as exc:
        print(f"ERROR: {str(exc)}")


@project.command()
@common_cli_params
@click.option('--id', help='Project ID', default=None)
@click.option('--name', help='Project name', default=None)
@click.option('--desc', help='Project Deescription', default=None)
def update(team, profile, id, name, desc):
    """
    Updates Project attributes
    \f
    Examples:
    \b
    $ iot project update --name "Project Name" --desc "..."
    """
    try:
        config = preload_config(team, profile)
        params = {}

        if name:
            params["project_name"] = name
        if id:
            params["project_id"] = id
        if desc:
            params["desc"] = desc

        url_params = urllib.parse.urlencode(params)
        url = f"project?{url_params}"
        print(f"Update Project URL: {url}")
        response = make_api_request('PUT', config, url)
        print(f"Response: {response}")
    except Exception as exc:
        print(f"ERROR: {str(exc)}")


@project.command()
@common_cli_params
@click.option('--name', help='Project name', default=None)
@click.option('--id', help='Project ID', default=None)
@click.option('--force', '-f', help='Force deletion without confirmation', default=False)
def delete(team, profile, name, id, force):
    """
    Delete an existing Project and all related elements
    \f
    Examples:
    \b
    $ iot project delete --name "..."
    """
    try:
        config = preload_config(team, profile)
        response = None

        if name:
            response = make_api_request('DELETE', config, f"project?project_name={name}")
        elif id:
            response = make_api_request('DELETE', config, f"project?project_id={id}")

        if response.status_code == 418:
            print(f"Invalid parameter. Record not found.")
            data = response.json()
            project_id = data.get('id', "")
            status = data.get('status', "")
            message = data.get('message', "")
            table = Table(show_header=True, header_style="bold green")
            table.add_column("Delete ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_column("Message")
            table.add_row(project_id, status, message)
            console.print(table)

        elif response.status_code == 200:
            delete_iot_project_dir(config.profile, name)
            data = response.json()
            project_id = data.get('id', "")
            status = data.get('status', "")
            table = Table(show_header=True, header_style="bold green")
            table.add_column("Deleted ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_row(project_id, status)
            console.print(table)

            # And now we go try to remove the local .iot/ files

    except Exception as exc:
        print(f"ERROR: {str(exc)}")

