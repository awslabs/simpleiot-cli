#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
import click
from simpleiot.cli.auth import auth
from simpleiot.cli.cloud import cloud
from simpleiot.cli.data import data
from simpleiot.cli.datatype import datatype
from simpleiot.cli.device import device
from simpleiot.cli.firmware import firmware
from simpleiot.cli.location import location
from simpleiot.cli.model import model
from simpleiot.cli.project import project
from simpleiot.cli.team import team
from simpleiot.cli.template import template
from simpleiot.cli.toolchain import toolchain
from simpleiot.cli.twin import twin
from simpleiot.cli.update import update

@click.group()
def iotcli():
    pass

iotcli.add_command(auth)
iotcli.add_command(cloud)
iotcli.add_command(data)
iotcli.add_command(datatype)
iotcli.add_command(device)
iotcli.add_command(firmware)
iotcli.add_command(location)
iotcli.add_command(model)
iotcli.add_command(project)
iotcli.add_command(team)
iotcli.add_command(template)
iotcli.add_command(toolchain)
iotcli.add_command(twin)
iotcli.add_command(update)


if __name__ == '__main__':
    iotcli()
