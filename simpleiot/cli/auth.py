#!/usr/bin/env python

# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
# This action allows user to authenticate against the Cognito/SSO userpool.
# Account credentials and the JWT token are stored in the local system secure pool.
# If username and password are specified, we overwrite any stored.
# They may also be specified in environment variables.
#
# The corresponding 'logout' action will log out and erase credentials.
#
import click
import json
from simpleiot.common.utils import *
from simpleiot.common.config import *

from rich import print
from rich.console import Console
import questionary
import boto3


console = Console()

# For this to work the Cognito user pool should have been set to ADMIN_NO_SRP_AUTH auth flow.
#
def _generate_token(config, username, password):
    access_token = None
    id_token = None
    cognito = None

    try:
        userpool = config.userpool
        client_id = config.client_id
        region = config.region

        if not userpool:
            print(f"INTERNAL ERROR: missing Cognito userpool in config file")
            exit(1)
        if not client_id:
            print(f"INTERNAL ERROR: missing Cognito Client ID in config file")
            exit(1)
        cognito = boto3.client('cognito-idp', region_name=region)
        resp = cognito.initiate_auth(
            ClientId=client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password
            }
        )

        access_token = resp['AuthenticationResult']['AccessToken']
        id_token = resp['AuthenticationResult']['IdToken']
    except cognito.exceptions.UserNotFoundException:
        print("ERROR: User not found")
    except cognito.exceptions.NotAuthorizedException:
        print("ERROR: login not authorized")
    except Exception as e:
        print(f"ERROR: {str(e)}")

    return access_token, id_token

@click.group()
def auth():
    """User Authentication"""
    pass

@auth.command()
@common_cli_params
@click.option("--username", "-user", help="Login username", envvar="IOT_USERNAME")
@click.option("--password", "-pass", help="Login password", envvar="IOT_PASSWORD")
@click.option("--clear", is_flag=True, help="Clear cached credentials")
def login(team, profile, username, password, clear):
    """
    Login to Team with auth credentials

    If a Team (specified in --team or via IOT_TEAM environment variable) specifies whether we've
    logged in using AWS SSO (Single Sign-on) we get credentials from the Keychain. If not specified
    we go through an SSO login process.

    If the team indicates that SimpleIOT was installed using standard Cognito login, this mechanism
    connects to Cognito and obtains a JWT token. The token is cached and used for subsequent connections
    to API gateway.

    If token is invalid, we'll quietly retry logging in using the cached username/password.
    These are stored in the local secure cache (i.e. Keychain for Mac).

    To get rid of all authentication tokens, add --clear to the command line.

    :return:
    """
    try:
        config = preload_config(team, profile)

        logged_in = False
        if clear:
            clear_all_auth(config)
            print("Done: Cached login credentials cleared")
            return

        if config.use_sso:
            # We assume if they're running this again, that they want fresh tokens obtained.
            #
            # access_key = get_stored_access_key(config)
            # access_secret = get_stored_access_secret(config)
            # session_token = get_stored_session_token(config)
            #
            # if access_key and access_secret and session_token:
            #     print("Logged in")
            # else:
            config_data = load_config(team)
            sso_url, sso_region, account_id, account_role, account_name, access_key, access_secret, session_token = \
                login_with_sso(config_data)
            if access_key:
                store_access_key(config, access_key)
            if access_secret:
                store_access_secret(config, access_secret)
            if session_token:
                store_session_token(config, session_token)
            print("Logged in")
        else:
            # If username or password is specified, we first check to see if we already have one in the
            # keyring. If so, these overwrite those (if different).
            # NOTE: stored username/password/taken routines are loaded from common.utils
            #
            stored_username = get_stored_username(config)
            stored_password = get_stored_password(config)

            if not username:
                username = stored_username

            while not username:
                username = questionary.text(f"Username:").ask()
                if not username:
                    print("Please enter username")

            if not password:
                password = stored_password

            while not password:
                password = questionary.password(f"Password:").ask()
                if not password:
                    print("Please enter password")

            # If password shows up with quotes on the outside, we try to strip it out.
            #
            password = unquote(password)
            access_token, id_token = _generate_token(config, username, password)
            if id_token:
                # print(f"Logged in with\nid_token: {id_token}\naccess_token: {access_token}")
                store_api_token(config, id_token)
                logged_in = True
                if username != stored_username:
                    store_username(config, username)
                if password != stored_password:
                    store_password(config, password)

            if logged_in:
                print(f"Logged in as user: {username}.")
            else:
                print(f"Failed to login.")
    except Exception as e:
        print(f"ERROR: {str(e)}")


@auth.command()
@common_cli_params
@click.option("--clear", is_flag=True, help="Clear cached credentials")
def logout(team, profile, clear):
    """
    Logout from Team and clear credentials
    """
    try:
        config = preload_config(team, profile)

        if clear:
            clear_all_auth(config)
            print("Done: All cached login credentials cleared")
        else:
            clear_api_token(config)
            print("Session logged out.")
    except Exception as e:
        print(f"ERROR: {str(e)}")


# @auth.command()
# @click.pass_obj
# @common_cli_params
# @click.option("--sso", prompt=True, help="SSO profile", envvar="IOT_SSO_PROFILE")
# def sso(team, profile, sso):
#     """
#     Login with Single-Sign-On
#     """
#     logged_in = False
#
#     try:
#         config = preload_config(team, profile)
#
#         region = config.region
#         if not profile:
#             profile = config.profile
#         if profile:
#             print(f"Logging in with SSO profile: {sso}")
#
#             boto3.setup_default_session(profile_name=sso, region_name=region)
#             sso_client = boto3.client('sso', region_name=region)
#             role_name = config.get("sso_role_name", "AdministratorAccess")
#             role_account = config.get("account", None)
#
#             # TODO: retrieve access token as described here:
#             # https://docs.aws.amazon.com/singlesignon/latest/OIDCAPIReference/API_CreateToken.html
#             #
#             access_token = None
#
#             if not role_account:
#                 print(f"ERROR: 'account' not configured in the config.json file for team")
#                 exit(1)
#
#             resp = sso_client.get_role_credentials(
#                 roleName=role_name, # Role (could be multiple)
#                 accountId=role_account, # sso_account_id,
#                 accessToken=access_token
#             )
#             access_id = resp['roleCredentials']['accessKeyId']
#             print(f"Got access ID: {access_id}")
#     except Exception as e:
#         print(f"ERROR: could not login using SSO: {str(e)}")
#         exit(1)
