#!/usr/bin/env python

# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
# Cloud installation:
#
# High-level:
#   install
#   update
#   uninstall
#   version
#   info
#
# Low-level:
#   terminal - used to shell into the container -- for debugging only.
#
import platform

import click
import os
import json
import time
from simpleiot.common.utils import *
from simpleiot.common.config import *
import signal
import sys
import subprocess
import docker

import urllib, urllib.parse
from rich import print
from rich.console import Console
from rich.table import Table
import requests
from pathlib import Path


DOCKER_IMAGE = "amazon/simpleiot-installer"
LOCAL_OUT_DIR = os.path.join(tempfile.gettempdir(), "simpleiot-layer")
SAVED_TEAM_NAME_FILE = "simpleiot_last_install_team.txt"

console = Console()

#
# This checks to see if the ~/.simpleiot directory exists or not. If not, it creates it so the
# docker mapping to the directory works.
#
def create_settings_if_not_exist():
    abs_path = os.path.expanduser("~/.simpleiot")
    if not os.path.exists(abs_path):
        os.mkdir(abs_path)

def clean_windows_path(src):
    split_path = os.path.splitdrive(src)
    prefix = (split_path[0][:1])
    suffix = Path(split_path[1]).as_posix()
    full_path = f"/{prefix}{suffix}"
    return full_path


def _invoke_unbuffered(command):
    try:
        if sys.platform == "win32":
            # For windows we use wexpect
            import msvcrt

            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
            os.system(command)

        else:
            result = os.system(command)
            print(result)
            #
            # # For mac or Linux we use pexpect
            # import subprocess
            # result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
            # print(result)

            # import pexpect
            #
            # c = pexpect.spawnu(command)
            # c.interact()
            # c.kill(1)

    except Exception as e:
        pass
    

def is_docker_on():
    result = False
    try:
        client = docker.from_env();
        client.ping()
        result = True
    except Exception as e:
        pass
    return result
#
# This command is a template for running the actual command inside the docker container
# that we have already installed. If not installed,
#
def run_in_docker(cmd, param=None, team=None):
    #
    # First, let's check and see if docker daemon is running
    #
    if is_docker_on():
        create_settings_if_not_exist()
        abs_aws_path = os.path.expanduser(os.path.join("~", ".aws"))
        abs_simpleiot_path = os.path.expanduser(os.path.join("~", ".simpleiot"))
        if not os.path.exists(LOCAL_OUT_DIR):
            os.mkdir(LOCAL_OUT_DIR)

        out_dir = Path(LOCAL_OUT_DIR).as_posix()

        if sys.platform == 'win32':
            abs_aws_path = clean_windows_path(abs_aws_path)
            abs_simpleiot_path = clean_windows_path(abs_simpleiot_path)
            out_dir = clean_windows_path(LOCAL_OUT_DIR)

        command = f"{cmd}"
        if param:
            command = f"{command} {param}"
        if team:
            command = f"{command} {team}"
        _invoke_unbuffered(f"docker pull {DOCKER_IMAGE}:latest")

        # os.system(f"docker run -i \
        _invoke_unbuffered(f"docker run -i \
                --network host \
                -v /var/run/docker.sock:/var/run/docker.sock \
                --mount type=bind,source={abs_aws_path},target=/root/.aws \
                --mount type=bind,source={abs_simpleiot_path},target=/root/.simpleiot \
                --mount type=bind,source={out_dir},target=/opt/iotapi/iotcdk/lib/lambda_src/layers/iot_import_layer/out \
                -t {DOCKER_IMAGE}:latest {command}")
    else:
        print(f"ERROR: Docker daemon is not running. Please start Docker desktop, then try again.")
        exit(1)

# After the bootstrap stage, the name of the team is saved in a temp file for use in subsequent
# stages.
#
# Ordinarily, this would need to be deleted, but we save it during bootstrap so we can look up
# the user-designated team name and pass it on to the next stage.
#
def load_team_from_tempfile(filename=SAVED_TEAM_NAME_FILE):
    try:
        tempdir = tempfile.gettempdir()
        infile = os.path.join(tempdir, filename)
        if os.path.exists(infile):
            with open(infile, 'r') as out:
                result = out.read().replace('\n','')
                return result
        else:
            return None
    except Exception as e:
        print(f"ERROR: could not read data from tempfile {filename}")
        raise e


@click.group()
def cloud():
    """Cloud back-end provisioning"""


@cloud.command()
def install():
    """
    Install cloud back-end for a single Team

    This command invokes docker to load and run the three stages of the install
    process. It first runs bootstrap, which asks for the name of the team. That is saved
    in a fixed file in the shared settings volume. Then it runs deploy with that team
    name. Once that is done, it runs the dbsetup phase.

    If you want to run each phase separately, best to do these not from inside the
    CLI but download and run the installer from source.

    NOTE: we will want to be careful running this on top of an existing installation.
    If it already exists, bad things may happen.

    """
    try:
        status = "OK"
        message = ""
        print("Loading installer image...")
        run_in_docker("invoke", "install")

        table = Table(show_header=True, header_style="green")
        table.add_column("Install Status")
        table.add_column("Message")
        table.add_row(status, message)
        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")


@cloud.command()
@common_cli_params
def uninstall(team, profile):
    """Uninstall cloud back-end for a Team"""
    try:
        status = "OK"
        message = ""
        print("Loading uninstaller image...")
        run_in_docker("invoke", "clean", team)

        table = Table(show_header=True, header_style="green")
        table.add_column("Uninstall Status")
        table.add_column("Message")
        table.add_row(status, message)

        console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")


@cloud.command()
def terminal():
    """For debugging: connect to installer container terminal"""
    create_settings_if_not_exist()
    abs_aws_path = os.path.expanduser(os.path.join("~", ".aws"))
    abs_simpleiot_path = os.path.expanduser(os.path.join("~", ".simpleiot"))
    if not os.path.exists(LOCAL_OUT_DIR):
        os.mkdir(LOCAL_OUT_DIR)

    out_dir = Path(LOCAL_OUT_DIR).as_posix()

    if sys.platform == 'win32':
        abs_aws_path = clean_windows_path(abs_aws_path)
        abs_simpleiot_path = clean_windows_path(abs_simpleiot_path)
        out_dir = clean_windows_path(LOCAL_OUT_DIR)

    # TODO: If the --user flag is needed on Windows, we need to extract the uid:gid using Windows APIs. getpwuid is a POSIX function.
    #
    if sys.platform == 'win32':
        user_flag = ""
    else:
        import pwd

        suid = pwd.getpwuid(os.getuid())
        uid = suid.pw_uid
        gid = suid.pw_gid
        user_flag = f"--user {uid}:{gid}"

    os.system(f"docker run -i \
            --network host \
            {user_flag} \
            -v /var/run/docker.sock:/var/run/docker.sock \
            --mount type=bind,source={abs_aws_path},target=/root/.aws \
            --mount type=bind,source={abs_simpleiot_path},target=/root/.simpleiot \
            --mount type=bind,source={out_dir},target=/opt/iotapi/iotcdk/lib/lambda_src/layers/iot_import_layer/out \
            -t {DOCKER_IMAGE}:latest /bin/bash")


