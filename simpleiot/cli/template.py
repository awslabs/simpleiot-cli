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
def template():
    """Project Template management"""


@template.command()
@common_cli_params
@click.option('--name', help='Template name', required=True)
@click.option('--desc', help='Template Description', default="")
@click.option('--type', help='Template Type', default="project")
@click.option('--icon', '-icon_url', help='Icon URL', default="")
@click.option('--author', help='Template author', default="")
@click.option('--email', help='Template author email', default="")
@click.option('--dev_url', help='Template developer URL', default="")
@click.option('--license', help='Template license', default="")
@click.option('--zip_url', '-zip', help='Template zip', default="")
@click.option('--file', '-f', help='Template value file', type=click.Path(exists=True))
def add(team, profile, name, desc, type, icon, author, email, dev_url, license, zip_url, file):
    """
    Define a new Project template
    \f
    Example:

    $ iot template add --name "..."
    """
    try:
        config = preload_config(team, profile)
        payload = {
            "name": name,
            "desc": desc
        }
        if type:
            payload["type"] = type
        if icon:
            payload["icon_url"] = icon
        if author:
            payload["author"] = author
        if email:
            payload["email"] = email
        if dev_url:
            payload["dev_url"] = dev_url
        if license:
            payload["license"] = license
        if zip_url:
            payload["zip_url"] = zip_url
        if file:
            with open(file, "r") as f:
                value = f.readlines()
            if value:
                payload['value'] = value

        response = make_api_request('POST', config, 'template', json=payload)
        if response:
            data = response.json()
            #
            # This creates the right local directory, if needed
            #
            table = Table(show_header=True, header_style="bold green")
            table.add_column("ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_column("Message")
            template_id = data.get("id", "")
            status = data.get("status", "ok")
            message = data.get("message", "")
            table.add_row(template_id, status, message)
            console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")


@template.command()
@common_cli_params
@click.option('--name', '--template', help='Template name', default=None)
@click.option('--id', help='Template ID', default=None)
@click.option('--full/--no-full', help='List Full Data', default=False)
def list(team, profile, name, id, full):
    """
    List defined Project templates
    \f
    Examples:

    $ iot template list --name "..."
    """
    try:
        config = preload_config(team, profile)
        multi = False

        if name:
            response = make_api_request('GET', config, f"template?name={name}")
        elif id:
            response = make_api_request('GET', config, f"template?id={id}")
        else:
            multi = True
            response = make_api_request('GET', config, f"template?all=true")

        data = response.json()

        if response:
            if full and not multi:
                show_detail(console, "Template", data)
                return

            table = Table(show_header=True, header_style="bold green")
            table.add_column("Template ID", style="dim", overflow="flow")
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
            table.add_column("Template List Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")


@template.command()
@common_cli_params
@click.option('--id', help='Template ID', default=None)
@click.option('--template_name', help='Template name', default=None)
@click.option('--name', help='New Template name', default=None)
@click.option('--desc', help='Template Deescription', default=None)
@click.option('--type', help='Template Type', default="project")
@click.option('--icon', '-icon_url', help='Icon URL', default="")
@click.option('--author', help='Template author', default="")
@click.option('--email', help='Template author email', default="")
@click.option('--dev_url', help='Template developer URL', default="")
@click.option('--license', help='Template license', default="")
@click.option('--zip_url', '-zip', help='Template zip', default="")
def update(team, profile, id, template_name, name, desc, type, icon, author, email, dev_url,
           license, zip_url):
    """
    Update Project Template attributes
    \f
    Updates information on templates already in system. Note: the value
    can not be modified (since it's a big JSON). To edit that, delete the old
    one and create a new one.

    Examples:
    \b
    $ iot template update --name "Template Name" --desc "..."
    """
    try:
        config = preload_config(team, profile)

        params = {}

        if name:
            params["name"] = name
        if id:
            params["id"] = id
        if template_name:
            params["new_name"] = name
        if desc:
            params["desc"] = desc
        if type:
            params["type"] = type
        if icon:
            params["icon_url"] = icon
        if author:
            params["author"] = author
        if email:
            params["email"] = email
        if dev_url:
            params["dev_url"] = dev_url
        if license:
            params["license"] = license
        if zip_url:
            params["zip_url"] = zip_url

        url_params = urllib.parse.urlencode(params)
        url = f"template?{url_params}"
        print(f"Update Template URL: {url}")
        response = make_api_request('PUT', config, url)
        print(f"Response: {response}")
    except Exception as e:
        print(f"ERROR: {str(e)}")


@template.command()
@common_cli_params
@click.option('--name', help='Template name', default=None)
@click.option('--id', help='Template ID', default=None)
def delete(team, profile, name, id):
    """
    Delete an existing Project Template
    \f
    Examples:
    \b
    $ iot template delete --name "..."
    """
    try:
        config = preload_config(team, profile)
        response = None

        if name:
            print(f"Deleting Template with name: '{name}'")
            response = make_api_request('DELETE', config, f"template?name={name}")
        elif id:
            print(f"Deleting Template with ID: '{id}'")
            response = make_api_request('DELETE', config, f"template?id={id}")

        if response.status_code == 418:
            print(f"Invalid parameter. Record not found.")
            data = response.json()
            template_id = data.get('id', "")
            status = data.get('status', "")
            message = data.get('message', "")
            table = Table(show_header=True, header_style="bold green")
            table.add_column("Delete ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_column("Message")
            table.add_row(template_id, status, message)
            console.print(table)

        elif response.status_code == 200:
            data = response.json()
            template_id = data.get('id', "")
            status = data.get('status', "")
            table = Table(show_header=True, header_style="bold green")
            table.add_column("Deleted ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_row(template_id, status)
            console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")
