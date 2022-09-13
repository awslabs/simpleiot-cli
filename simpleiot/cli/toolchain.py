#!/usr/bin/env python

# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
# This command manages build toolchains. It is here to allow
# the build toolchain to be easily installed. It currently supports local install of
# the arduino-cli for ESP32, but is intended so it can be extended to Docker-based
# local as well as remote Cloud-based installations.
#
# It is also intended to be cross-platform (Mac/Win)
# The operations available are:
#
# - toolchain install: install one or more versions of the toolchain.
# - toolchain update: update to the latest version of the toolchain.
# - toolchain uninstall: remove.
# - toolchain list: list all the toolchains available for building.
#

import click
from simpleiot.common.utils import *
from simpleiot.common.config import *
from simpleiot.cli.buildtool.toolchain import Toolchain
from simpleiot.cli.buildtool.toolchainbase import ToolchainLocation

from rich import print
from rich.console import Console
from rich.table import Table
import serial.tools.list_ports
import questionary
import tempfile
import os
import zipfile
from pathlib import Path
from shutil import which
import requests
import platform
import tempfile


#
# NOTE: the toolchain directory starts with an underline. When listing all the teams installed
# we specifically exclude directory names that start with and underline. This way, we can find all local teams
# simply by scanning the contents of the ~/.simpleiot directory instead of managing a local registry which can
# fall out of sync if someone messes with the directory.
#
console = Console()
toolchain_class = Toolchain()

# Update this with latest ESP32 toolchain version getting installed.
# For non-Arduino toolchains, we will need a central registry.
#
LATEST_ARDUINO_ESP32_TOOLCHAIN_VERSION="3.3.0"


@click.group()
def toolchain():
    """Project Template management"""

@toolchain.command()
@click.option("--base", "--path", help="Base path of toolchain", default=Toolchain.base())
@click.option("--alias", "--nickname", help="Toolchain alias", default="esp32arloc")
@click.option("--manufacturer", "--brand", help="Manufacturer name", default="espressif")
@click.option("--processor", "--cpu", help="Processor type", default="esp32")
@click.option("--os", "os_", help="Operating system name", default="arduino")
@click.option("--version", help="Toolchain version", default=LATEST_ARDUINO_ESP32_TOOLCHAIN_VERSION)
@click.option("--verbose", "-v", help="Verbose", is_flag=True, default=False)
@click.option("--location", help="Install location type",
              type=click.Choice(["local", "local_container", "cloud_container", "cloud_server"], case_sensitive=False),
              default="local")
def install(base, alias, manufacturer, processor, os_, version, verbose, location):
    """
    Install the toolchain given manufacturer, processor, OS, and version.
    Defaults to the DevKit: Espressif:ESP32:Arduino:latest:Local.

    Location can be:
      - **local** or **native**: Installed on the local filesystem.
      - **local_container**: Installed as a pre-built Docker image. Assumes Docker desktop is installed.
      - **cloud_container**: Installed in your own account as an ECS container.
      - **cloud_server**: Pointed at a centralized development Cloud installation.

    Currently only the local option is supported.

    The `--team` parameter needs to be specified since we keep track of installations
    inside the local team configuration file.

    If a toolchain is already installed, this command will fail. To reinstall you have to first
    uninstall that version and then reinstall it using this command.

    \f
    Example:

    $ not toolchain install
    """
    global toolchain_class
    try:
        location_enum = ToolchainLocation(location)
        if verbose:
            print(f"+ Location: {location_enum}")

        from yaspin import yaspin

        with yaspin(text="Installing... ", color="green") as spinner:
            if alias:
                if verbose:
                    print(f"+ Installing for alias {alias} to base {base}")

                result = toolchain_class.install_alias(base, alias, verbose)
                if verbose:
                    print(f"+Install result: {result}")
                # print(f"Install result: {result}")
            else:
                print(f"+ Install base: {base} mfr: {manufacturer} proc: {processor} os: {os_} vers: {version}, loc: {location_enum}")
                toolchain_class.install(base, manufacturer, processor, os_, version, location_enum, verbose)

            if verbose:
                print("Resetting toolchain...")
            toolchain_class.reset(base, manufacturer, processor, os_, version, location_enum, verbose)
            spinner.ok("✅ ")

    except Exception as e:
        print(f"ERROR: {str(e)}")


@toolchain.command()
@click.option("--base", "--path", help="Base path of toolchain", default=Toolchain.base())
@click.option("--alias", "--nickname", help="Toolchain alias", default=None)
@click.option("--manufacturer", "--brand", help="Manufacturer name", default="espressif")
@click.option("--processor", "--cpu", help="Processor type", default="esp32")
@click.option("--os", "os_", help="Operating system name", default="arduino")
@click.option("--version", help="Toolchain current version", default=None)
@click.option("--to", help="Toolchain desired version", default=None)
@click.option("--verbose", "-v", help="Verbose", is_flag=True, default=False)
def update(base, alias, manufacturer, processor, os_, version, to, verbose):
    """
    Update installed toolchain to given version.
    """
    global toolchain_class
    try:
        print("Not available yet.")

    except Exception as e:
        print(f"ERROR: {str(e)}")


@toolchain.command()
@click.option("--base", "--path", help="Base path of toolchain", default=Toolchain.base())
@click.option("--alias", "--nickname", help="Toolchain alias")
@click.option("--manufacturer", "--brand", help="Maunfacturer name", default="espressif")
@click.option("--processor", "--cpu", help="Processor type", default="esp32")
@click.option("--os", "os_", help="Operating system name", default="arduino")
@click.option("--version", help="Toolchain current version", default=LATEST_ARDUINO_ESP32_TOOLCHAIN_VERSION)
@click.option("--location", help="Install location type",
              type=click.Choice(["local", "local_container", "cloud_container", "cloud_server"], case_sensitive=False),
              default="local")
@click.option("--verbose", "-v", help="Verbose", is_flag=True, default=False)
def uninstall(base, alias, manufacturer, processor, os_, version, location, verbose):
    """
    Remove installed toolchain.
    """
    global toolchain_class
    try:
        location_enum = ToolchainLocation(location)

        if alias:
            result = toolchain_class.uninstall(base, alias, verbose)
        else:
            result = toolchain_class.uninstall(base, manufacturer, processor, os_, version, location_enum, verbose)
    except Exception as e:
        print(f"ERROR: {str(e)}")

#
# NOTE: the version number must match the default version of the toolchain installed for the platform.
# If it isn't installed, we'll have to go find it from a central registry. For now, however, we default to
# the current latest version.
#

@toolchain.command()
@click.option("--base", "--path", help="Base path of toolchain", default=Toolchain.base())
@click.option("--manufacturer", "--brand", help="Manufacturer name", default="espressif")
@click.option("--processor", "--cpu", help="Processor type", default="esp32")
@click.option("--os", "os_", help="Operating system name", default="arduino")
@click.option("--version", help="Toolchain current version", default=LATEST_ARDUINO_ESP32_TOOLCHAIN_VERSION)
@click.option("--location", help="Install location type",
              type=click.Choice(["local", "local_container", "cloud_container", "cloud_server"], case_sensitive=False),
              default="local")
@click.option("--verbose", "-v", help="Verbose", is_flag=True, default=False)
def reset(base, manufacturer, processor, os_, version, location, verbose):
    """
    Remove installed toolchain.
    """
    global toolchain_class
    try:
        location_enum = ToolchainLocation(location)
        result = toolchain_class.reset(base, manufacturer, processor, os_, version, location_enum, verbose)
    except Exception as e:
        print(f"ERROR: {str(e)}")


@toolchain.command()
@click.option("--manufacturer", "--brand", help="Maunfacturer name", default="espressif")
@click.option("--processor", "--cpu", help="Processor type", default="esp32")
@click.option("--os", "os_", help="Operating system name", default="arduino")
def list(manufacturer, processor, os_):
    """
    List available and/or installed toolchains on this machine. This is loaded out of the
    .simpleiot/toolchain.json file.
    """
    global toolchain_class
    try:
        print("Not Implemented. Check back soon.")

    except Exception as e:
        print(f"ERROR: {str(e)}")


@toolchain.command()
def available():
    """
    List available and/or installed toolchains.

    This scans through the list of registered toolchain subclasses and shows what can be
    installed.
    """
    global toolchain_class
    try:
        toolchain_list = toolchain_class.list_available()
        table = Table(show_header=True, header_style="green")
        table.add_column("Alias", style="bold", overflow="flow")
        table.add_column("Name", style="bold", overflow="flow")
        table.add_column("Mfr", style="bold", overflow="flow")
        table.add_column("Proc", style="bold", overflow="flow")
        table.add_column("OS", style="bold", overflow="flow")
        table.add_column("Version", style="bold", overflow="flow")
        table.add_column("Location", style="bold", overflow="flow")

        for _, tool in toolchain_list.items():
            table.add_row(tool.alias,
                          tool.name,
                          tool.manufacturer,
                          tool.processor,
                          tool.opsys,
                          tool.version,
                          tool.location.name)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")

