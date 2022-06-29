#!/usr/bin/env python

# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
# Support for fixed physical locations, for example, homes, offices, schools, stores, etc.

import click
from simpleiot.common.utils import *
from simpleiot.common.config import *

import urllib, urllib.parse
from rich import print
from rich.console import Console
from rich.table import Table
import requests

##################################

console = Console()


@click.group()
def location():
    """Location management"""

@location.command()
@common_cli_params
@click.option("--name", help="Location name", required=True)
@click.option("--desc", help="Location Description", default="")
@click.option("--address", help="Location Address", default="")
@click.option("--image", help="Location Image", default=None)
@click.option("--bg", help="Location Background Image", default=None)
@click.option("--map", help="Location Indoor map URL", default=None)
@click.option("--latitude", "--lat", help="Location Latitude", default=None)
@click.option("--longitude", "--lng", help="Location Longitude", default=None)
@click.option("--altitude", "--alt", help="Location Altitude", default=None)
def add(team, profile, name, desc, address, image, bg, map,
        latitude, longitude, altitude):
    """
    Define a new location
    \f
    Examples:

    $ iot location add --name "..." --address "..."

    """
    try:
        config = preload_config(team, profile)

        payload = {
            "name": name,
            "address": address,
        }
        if desc:
            payload["desc"] = desc
        if latitude:
            payload["geo_lat"] = latitude
        if latitude:
            payload["geo_ng"] = longitude
        if altitude:
            payload["geo_alt"] = altitude
        if image:
            payload["image_url"] = image
        if bg:
            payload["bg_url"] = bg
        if map:
            payload["indoor_map_url"] = map

        response = make_api_request("POST", config, "location", json=payload)
        data = response.json()

        if response.status_code == requests.codes.ok:
            location_id = data["id"]
            table = Table(show_header=True, header_style="green")
            table.add_column("ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_row(location_id, "OK")
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


@location.command()
@common_cli_params
@click.option("--name", help="Location name", default=None)
@click.option("--id", help="Location ID", default=None)
@click.option("--full/--no-full", help="List Full Data", default=False)
def list(team, profile, name, id, full):
    """
    List already defined locations
    \f
    Examples:
    \b
    $ iot location list --id "..."
    """
    try:
        config = preload_config(team, profile)

        multi = False

        if name:
            response = make_api_request("GET", config, f"location?name={name}")
        elif id:
            response = make_api_request("GET", config, f"location?id={id}")
        else:
            multi = True
            response = make_api_request("GET", config, f"location?all=true")

        data = response.json()
        if response.status_code == requests.codes.ok:
            if full and not multi:
                show_detail(console, "Location", data)
                return

            table = Table(show_header=True, header_style="green")
            table.add_column("Location ID", style="dim", overflow="flow")
            table.add_column("Name")
            table.add_column("Address")
            table.add_column("Date Created", justify="right")
            if multi:
                for d in data:
                    id = d.get("id", "***")
                    name = d.get("name", "***")
                    address = d.get("address", "***")
                    created = d.get("date_created", "***")
                    table.add_row(id, name, address, format_date(created))
            else:
                id = data.get("id", "***")
                name = data.get("name", "***")
                address = data.get("address", "***")
                created = data.get("date_created", "***")
                table.add_row(id, name, address, format_date(created))
        else:
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("Location List Status")
            table.add_column("Message")
            table.add_row(status, message)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")


@location.command()
@common_cli_params
@click.option("--id", help="Location ID", required=True)
@click.option("--name", help="Location name", required=True)
@click.option("--desc", help="Location Description", default="")
@click.option("--address", help="Location Address", default="")
@click.option("--image", help="Location Image", default=None)
@click.option("--bg", help="Location Background Image", default=None)
@click.option("--map", help="Location Indoor map URL", default=None)
@click.option("--latitude", "--lat", help="Location Latitude", default=None)
@click.option("--longitude", "--lng", help="Location Longitude", default=None)
@click.option("--altitude", "--alt", help="Location Altitude", default=None)
def update(team, profile, id, name, desc, address, image, bg, map,
        latitude, longitude, altitude):
    """
    Update Location attributes
    \f
    Examples:

    $ iot location update --name "..." --address "..."
    """
    try:
        config = preload_config(team, profile)

        payload = {
            "id": id,
        }
        if name:
            payload["name"] = name
        if desc:
            payload["desc"] = desc
        if desc:
            payload["address"] = address
        if image:
            payload["image"] = image
        if bg:
            payload["bg"] = bg
        if map:
            payload["map"] = map
        if latitude:
            payload["lat"] = latitude
        if longitude:
            payload["lng"] = longitude
        if altitude:
            payload["alt"] =  altitude

        url_params = urllib.parse.urlencode(payload)
        url = f"location?{url_params}"
        response = make_api_request('PUT', config, url)
        data = response.json()

        if response.status_code == requests.codes.ok:
            location_id = data.get("id", "***")
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="bold green")
            table.add_column("Location ID", style="dim", overflow="flow")
            table.add_column("Status")
            table.add_column("Message")
            table.add_row(location_id, status, message)
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


@location.command()
@common_cli_params
@click.option("--name", help="Location name", default=None)
@click.option("--id", help="Location ID", default=None)
def delete(team, profile, name, id):
    """Deletes an already-defined location
    \f
    Examples:
    \b
    $ iot location delete --id "..."
    """
    try:
        config = preload_config(team, profile)

        response = None

        if name:
            response = make_api_request("DELETE", config, f"location?name={name}")
        elif id:
            response = make_api_request("DELETE", config, f"location?id={id}")

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
