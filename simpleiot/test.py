#!/usr/bin/env python

# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
# This is a test script for the CLI, using the click CliRunner tool. To run, use
# pytest. Note that the following environment variables should be set in order for
# the test to work:
#
# IOT_TEAM: team name to test against
# IOT_USERNAME: userid of valid account
# IOT_PASSWORD: password for valid account
#

import os
from click.testing import CliRunner
from simpleiot.iot import iotcli

def check_auth():
    """
    Basic check that the environment variables everty command needs are set.
    """
    runner = CliRunner()
    assert runner

    team = os.getenv("IOT_TEAM")
    username = os.getenv("IOT_USERNAME")
    password = os.getenv("IOT_PASSWORD")
    assert team
    assert username
    assert password

    return runner, team, username, password


def check_login():
    """
    Performs standard login to make sure we have an auth token to use for
    subsequent interactions.
    """
    runner, team, username, password = check_auth()
    result = runner.invoke(iotcli, ['auth', 'login', f"--username={username}", f"--password={password}"])
    assert result.exit_code == 0
    assert "ERROR" not in result.output
    return runner


def test_help():
    """
    Basic test to see that the command is available
    """
    runner, team, username, password = check_auth()
    result = runner.invoke(iotcli, ['--help'])
    assert result.exit_code == 0


def test_auth_login_logout():
    """
    Login/Logout with (hopefully) valid user.
    """
    runner = check_login()
    result = runner.invoke(iotcli, ['auth', 'logout', "--clear"])
    assert result.exit_code == 0
    assert "ERROR" not in result.output


def test_bad_auth_login_logout():
    """
    Test for invalid username/password combos. These tests should fail.
    """
    runner, team, username, password = check_auth()

    bad_username = "BAD_USER_XXX"
    bad_password = "BAD_PASSWORD_XXX"

    result = runner.invoke(iotcli, ['auth', 'login', f"--username={bad_username}", f"--password={password}"])
    assert result.exit_code == 0
    assert "ERROR" in result.output

    result = runner.invoke(iotcli, ['auth', 'login', f"--username={username}", f"--password={bad_password}"])
    assert result.exit_code == 0
    assert "ERROR" in result.output

    result = runner.invoke(iotcli, ['auth', 'login', f"--username={bad_username}", f"--password={bad_password}"])
    assert result.exit_code == 0
    assert "ERROR" in result.output

    result = runner.invoke(iotcli, ['auth', 'logout', "--clear"])
    assert result.exit_code == 0
    assert "ERROR" not in result.output


def test_project_list_all():
    """
    Get a list of all projects. We check for the word "ERROR" in the return.
    """
    runner = check_login()
    result = runner.invoke(iotcli, ['project', 'list'])
    assert result.exit_code == 0
    assert "ERROR" not in result.output

def test_project_add_then_delete():
    """
    Test for adding a new blank project, verifying that the name is returned when listing
    projects, then cleaning it up. Due to the way tables are aligned some of the names may
    be truncated, so we truncate the test names to make sure we don't accidentally return
    a false negative.
    """
    project_name = "test_plain_proj"
    runner = check_login()
    result = runner.invoke(iotcli, ['project', 'add', f"--name={project_name}"])
    assert result.exit_code == 0
    assert "ERROR" not in result.output

    result = runner.invoke(iotcli, ['project', 'list', f"--name={project_name}"])
    assert result.exit_code == 0
    assert project_name[1:6] in result.output
    assert "ERROR" not in result.output
    assert project_name[1:6] in result.output

    result = runner.invoke(iotcli, ['project', 'delete', f"--name={project_name}"])
    assert "ERROR" not in result.output

    result = runner.invoke(iotcli, ['project', 'list', f"--name={project_name}"])
    assert "error" in result.output


def test_project_create_template_then_delete():
    """
    This test creates a project based on a built-in template, then checks to make sure
    all the sub-components like Model and Datatype are present. It then cleans up the project
    And checks to make sure the values are no longer present.

    If this test fails, the project/model/datatypes may have to be manually cleaned up.
    """
    project_name = "test_template_proj"
    template_name = "HelloWorldM5"
    model_name = "HelloWorldModel"

    runner = check_login()

    result = runner.invoke(iotcli, ['project', 'add', f"--name={project_name}", f"--template={template_name}"])
    assert result.exit_code == 0
    assert "ERROR" not in result.output

    result = runner.invoke(iotcli, ['project', 'list', f"--name={project_name}"])
    assert result.exit_code == 0
    assert project_name[1:6] in result.output
    assert "ERROR" not in result.output

    result = runner.invoke(iotcli, ['model', 'list', f"--project={project_name}", f"--model={model_name}"])
    assert result.exit_code == 0
    assert "ERROR" not in result.output
    assert project_name[1:6] in result.output
    assert model_name[1:6] in result.output

    result = runner.invoke(iotcli, ['datatype', 'list', f"--project={project_name}", f"--model={model_name}"])
    assert result.exit_code == 0
    assert "ERROR" not in result.output
    assert project_name[1:6] in result.output
    assert model_name[1:6] in result.output
    assert "button" in result.output
    assert "color" in result.output

    result = runner.invoke(iotcli, ['project', 'delete', f"--name={project_name}"])
    assert result.exit_code == 0
    assert "ERROR" not in result.output

    result = runner.invoke(iotcli, ['datatype', 'list', f"--project={project_name}", f"--model={model_name}"])
    assert "error" in result.output

    result = runner.invoke(iotcli, ['model', 'list', f"--project={project_name}", f"--model={model_name}"])
    assert "error" in result.output

    result = runner.invoke(iotcli, ['project', 'list', f"--name={project_name}"])
    assert "error" in result.output
