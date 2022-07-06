#!/usr/bin/env python

# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
# The person who does the installation gets a lot of information that others
# don't need. For example, database passwords, and whatnot. However, subsequent
# users need to be able to access the same back-end and interact with it.
#
# To allow this to happen, you can 'join' a team and receive the credentials
# necessary to access the environment's resources. In the future we may want
# to use this to create more fine-grain access to resources, but for now,
# it just handles the situation where someone can get a subset of the credentials
# onto their machine so they can co-develop.
#
# By leaving a team, the team credentials for that profile will be removed from the
# local directory.
#
# At this point, this is a pretty lightweight operation. We may want to register it
# on the cloud at some point, if further tracking and logging is needed.
#
# We will also be revving this further when dealing with fine-grained accounts
# and roles.
#
import click
from simpleiot.common.utils import *
from simpleiot.common.config import *

from rich import print
from rich.console import Console
from rich.table import Table
import boto3
import questionary
from cryptography.fernet import Fernet
import base64
import time
from operator import itemgetter


console = Console()


@click.group()
def team():
    """Team management (CLI only)"""


#
# List displays all the teams in the current system. It has both short and full versions.
# It lists teams, based on what's available in the ~/.simpleiot directory. If a team name is specified
# we will display the full version.
#
@team.command()
@click.option("--team", "--name", help="Team name")
def list(team):
    """
    List known teams
    """
    try:
        if team:
            config = load_config(team)
            if not config:
                print(f"ERROR: team [ {team} ] not found.")
                exit(0)

            data = {
                "Team Name": config.get("team", "***"),
                "Organization": config.get("org_name", "***"),
                "AWS Account #": config.get("account", "***"),
                "Admin Email": config.get("admin_email", "***"),
                "Dashboard URL": _linkify(config.get("web_endpoint", "***")),
                "REST API URL": _linkify(config.get("apiEndpoint", "***")),
                "IOT Endpoint": _linkify(config.get("iot_endpoint", "***")),
                "Date Installed": config.get("install_utc_time", "***")
            }
            show_detail(console, "Team", data)
        else:
            team_data = list_all_teams()
            ordered_list = sorted(team_data.keys())
            table = Table(show_header=True, header_style="green")
            table.add_column("Team", style="dim", overflow="flow")
            table.add_column("Org")
            table.add_column("Date Installed", justify="right")
            for one_team in ordered_list:
                data = team_data[one_team]
                install_date = data.get("install_utc_time", None)
                if install_date:
                    install_date = format_date(install_date)
                else:
                    install_date = "***"
                table.add_row(one_team, data["org_name"], install_date)

            console.print(table)
    except Exception as e:
        print(f"ERROR: can not list teams. {str(e)}")
        exit(1)

def _linkify(link):
    result = None
    if link == "***":
        result = link
    else:
        result = f"[link=\"{link}\"]{link}[/link]"
    return result

#
# Invite is used by the admin to send invites to other team members.
# It collects the bare minimum information that is needed to get someone else to join.
# As a simple security measure (until we get proper roles), it checks to see if the
# bootstrap file is present and has information that indicates the user is the
# installer.
#
# NOTE: this user must be added to the Cognito pool (or if SSO, we assume it
# exists.
#
@team.command()
@common_cli_params
@click.option("--username", "-user", help="Username", required=True)
@click.option("--email", "-email", help="User email", required=True)
@click.option("--alias", "-as", help="Invite Team Alias")
@click.option("--path", "-p", help="Output Path for Invite file", default=".")
def invite(team, profile, username, email, alias, path):
    """
    Registers a new user and generates an invite file.
    """
    try:
        config = preload_config(team, profile)
        account = _is_admin(config)
        if not account:
            print("ERROR: invites can only be sent out by the administrator.")
            exit(1)

        if not os.path.isdir(path):
            print(f"ERROR: output path [{path}] does not exist")
            exit(1)

        temp_password = _add_user(config, username, email)
        if temp_password:
            team_as = config.team
            if alias:
                team_as = alias
            output_file_prefix = f"invite_{team_as}_{username}"
            invite_path = os.path.join(path, f"{output_file_prefix}.simpleiot")
            key = _create_invite(config, account, invite_path, username, email, temp_password)
            if key:
                print(f"DONE:\nInvite Key: {key}\nFile: {invite_path}")
                print("\nSend files and key to recipient and have them join via CLI\n\n% iot team join --invite {filename}.")
            else:
                print(f"ERROR saving invite files to path: '{path}'")

    except Exception as e:
        print(f"ERROR: can not send invite. {str(e)}")
        exit(1)

#
# Add a user to Cognito. If successful, we return the temporary password generated
# for the account. If not, we return None and let the caller deal with it.
# If username is a dupe or the password is invalid, we signal it here and return None.
#
def _add_user(config, username, email):
    temp_password = None
    try:
        local_config = load_config(config.team)
        use_sso = local_config.get("use_sso", False)
        if not use_sso:
            region = local_config.get("region", None)
            user_pool_id = local_config.get("cognitoUserPoolId", None)
            profile = local_config.get("aws_profile", "default")
            os.environ['AWS_PROFILE'] = profile
            temp_password = generate_temp_password()
            cognito = boto3.client('cognito-idp', region_name=region)
            response = cognito.admin_create_user(
                UserPoolId=user_pool_id,
                Username=username,
                TemporaryPassword=temp_password,
                UserAttributes=[
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "email", "Value": email}
                ],
                MessageAction='SUPPRESS'
            )
            result = True
    except ClientError as e:
        temp_password = None
        code = e.response['Error']['Code']
        if code == "UsernameExistsException":
            print(f"ERROR: user {username} already exists.")
        elif code == "InvalidPasswordException":
            print(f"ERROR: password invalid. Please delete user and try again.")
        else:
            print(f"ERROR: {str(e)}")

    return temp_password

#
# This uses an invitation file filled with encrypted data needed to join.
# It returns the key if the invitation was created. The path in which we want the
# invitation is written is passed down. In single-invite mode, the caller can pass the
# name of the invite. In bulk-mode, the routine calling us will have created a temporary
# file in the tmp directory.
#
def _create_invite(config, account, invite_path, username, email, temp_password):
    result = None
    try:
        team = config.team
        local_config = load_config(team)
        use_sso = local_config.get("use_sso", False)
        if not use_sso:
            region = local_config.get("region", None)
            org_name = local_config.get("org_name", None)
            api_endpoint = local_config.get("apiEndpoint", None)
            iot_endpoint = local_config.get("iot_endpoint", None)
            cognito_identity = local_config.get("cognitoIdentityPoolId", None)
            cognito_client_id = local_config.get("cognitoClientId", None)
            cognito_user_pool_id = local_config.get("cognitoUserPoolId", None)
            dashboard_url = local_config.get("dashboardDomainName", None)

            mqtt_port = local_config.get("mqtt_port", 8883)
            payload = {
                "team": team,
                "region": region,
                "account": account,
                "username": username,
                "temp_password": temp_password,
                "email": email,
                "org_name": org_name,
                "use_sso": use_sso,
                "apiEndpoint": api_endpoint,
                "iot_endpoint": iot_endpoint,
                "mqtt_port": mqtt_port,
                "cognitoIdentityPoolId": cognito_identity,
                "cognitoClientId": cognito_client_id,
                "cognitoUserPoolId": cognito_user_pool_id,
                "dashboard_url": f"https://{dashboard_url}"
            }

        if use_sso:
            bootstrap = load_bootstrap_config(team)
            payload["sso_url"] = bootstrap.get("sso_url")
            username = "sso"

        key, payload_str = _encrypt_invite(payload)

        # This could also generate a QRCode file with above data.
        # To be used when logging in from mobile or something with a camera.
        #
        # write_qr_file(path, output_file_prefix, "qrcode", payload_str)
        #
        with open(invite_path, 'w', encoding='utf-8') as outfile:
            outfile.write(payload_str)

        result = key
    except Exception as e:
        print(f"ERROR: can not generate invite file. {str(e)}")

    return result


@team.command()
@common_cli_params
@click.option("--input", "-i", help="Input CSV file", default="invite.csv")
@click.option("--alias", "-as", help="Invite Team Alias")
@click.option("--mailconf", help="Email config file", default="simpleiotmail.conf")
@click.option("--via", help="Mailing service, default is 'ses'", default="ses")
def bulkinvite(team, profile, input, alias, mailconf, via):
    """
    Bulk user addition with email invitation.
    """
    try:
        config = preload_config(team, profile)

        import email, smtplib, ssl
        from email import encoders
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        import tempfile
        from configparser import ConfigParser
        import csv
        import os
        import shutil

        smtp_server = None
        smtp_port = None
        smtp_username = None
        smtp_password = None
        from_email = None
        server = None

        EMAIL_CIPHERS = ('ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
            'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:!eNULL:!MD5')
        team = config.team

        # First we do our check to see if this is on the admin machine.
        # TODO: if we move to a container-based installation, this test will have to be reevaluated.
        #
        account = _is_admin(config)
        if not account:
            print("ERROR: bulk invites can only be sent out by the system installer.")
            exit(1)

        # Check the config file. It should have at least the port/server/username/password
        # values.
        #
        if not os.path.exists(mailconf):
            print(f"ERROR: Bulk email configuration file [{mailconf}] not found.")
            exit(1)

        try:
            config_p = ConfigParser()
            with open(mailconf, encoding='utf-8') as email_input:
                #
                # We look for a section header in the config file that matches the 'via' keyword.
                # This way, they can switch to different email providers.
                # If none is specified, we may want to attach a default section
                #
                # default_config = "[default]\n" + email_input.read()
                # config_p.read_string(default_config)

                config_p.read_string(email_input.read())

            section = config_p[via]
            smtp_port = section.get('smtp_port', '587')
            smtp_server = section['smtp_server']
            smtp_username = section['smtp_username']
            smtp_password = section['smtp_password']
            from_email = section['from_email']

            if not (smtp_port and smtp_server and smtp_username and smtp_password and from_email):
                print(f"ERROR: SMTP email configuration values missing in '{mailconf}'")
                exit(1)

            # First we try to connect to the SMTP server. If it fails, we don't create extra
            # users.
            #
            try:
                print(f"Trying to to connect to mail server: {smtp_server} on port {smtp_port}")

                server = smtplib.SMTP(smtp_server, port=smtp_port)
                if not server:
                    print(f"ERROR: could not create a connection to the SMTP server {smtp_server} on port {smtp_port}")
                    print(f"       Please remove users and re-run again.")
                    exit(1)

                server.ehlo()  # send the extended hello to our server

                # only TLSv1 or higher
                context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
                context.options |= ssl.OP_NO_SSLv2
                context.options |= ssl.OP_NO_SSLv3

                context.set_ciphers(EMAIL_CIPHERS)
                context.set_default_verify_paths()
                context.verify_mode = ssl.CERT_REQUIRED

                if server.starttls(context=context)[0] != 220:
                    print("ERROR: could not connect securely to email server")
                    exit(1)

                print(f"Logging in to mail server with username: {smtp_username}.")
                server.login(smtp_username, smtp_password)

            except Exception as e:
                print(f"ERROR: Error connecting to server: {str(e)}")
                exit(1)

        except Exception as e:
            print(f"ERROR: Error loading section '{via}' in bulk email configuration file '{mailconf}'")
            exit(1)

        if not os.path.exists(input):
            print(f"ERROR: input CSV file [{input}] does not exist.")
            exit(1)

        invite_list = []
        temp_dir = tempfile.mkdtemp() # where we stage the inputs

        with open(input, newline='', encoding='utf-8') as csvfile:
            recipient_reader = csv.reader(csvfile)
            for row in recipient_reader:
                invite_email = unquote(row[0])
                if invite_email == "email":
                    continue
                invite_username = unquote(row[1])

                account = _is_admin(config)
                if not account:
                    print("ERROR: invites can only be sent out by the administrator.")
                    exit(1)

                temp_password = _add_user(config, invite_username, invite_email)
                if not temp_password:
                    print(f"ERROR: could not add user named '{invite_username}' -- skipping")
                    continue

                team_as = team
                if alias:
                    team_as = alias

                output_file_prefix = f"invite_{team_as}_{invite_username}"
                invite_filename = f"{output_file_prefix}.simpleiot"
                invite_path = os.path.join(temp_dir, invite_filename)
                key = _create_invite(config, account, invite_path, invite_username, invite_email, temp_password)
                if key:
                    invite = {
                        "username": invite_username,
                        "email": invite_email,
                        "invite_file": invite_filename,
                        "invite_path": invite_path,
                    }
                    invite_list.append(invite)

                    invite_body = f"""
                    You have been invited to join the '{team}' SimpleIOT Team!
                    
                    To join, you will need to:
                    
                    1) Install the SimpleIOT command-line interface. Instructions are at: http://simpleiot.net.
                    2) Save the attached invitation file to your local file system.
                    3) Copy/paste the temporary key below. You will be asked for it in the next step.
                    
                       {key}
                    
                    4) Invoke the command:
                    
                       iot join --invite={{path-to-invite-file}} --key='{key}'
                       
                    5) You will be asked to enter a password for your account. It should contain upper and lower case, digits, and a special character.
                    6) If successful, you will be shown your team name and the link to your team's web dashboard.
                    7) You can login to the dashboard with your username '{invite_username}' and your chosen password.
                    8) For command-line access, please login with:
                    
                       iot login --team={team_as} --username={invite_username}
                       
                    You will be prompted for your chosen password.
                    
                    Congratulations! Now you are ready to use the SimpleIOT system.
                    
                    Please proceed with the workshop or tutorial to see how easy it is to create a cloud-connected devices.
                    """
                    invite["body"] = str(invite_body)
                else:
                    print(f"ERROR saving invite files to path: '{invite_path}' -- skipping")

                if server:
                    for one in invite_list:
                        recipient_email = one["email"]
                        print(f"Sending email invite to: '{recipient_email}'")
                        message = MIMEMultipart()
                        message["From"] = from_email
                        message["To"] = recipient_email
                        message["Subject"] = "SimpleIOT Invite"
                        message.attach(MIMEText(one["body"], "plain"))

                        # Open PDF file in binary mode
                        invite_path = one["invite_path"]
                        with open(invite_path, "rb") as attachment:
                            part = MIMEBase("application", "octet-stream")
                            part.set_payload(attachment.read())

                        # Encode file in ASCII characters to send by email
                        encoders.encode_base64(part)

                        # Add header as key/value pair to attachment part
                        filename = one["invite_file"]
                        part.add_header(
                            "Content-Disposition",
                            f"attachment; filename= {filename}"
                        )
                        message.attach(part)
                        text = str(message.as_string())

                        rec_user = one["username"]
                        rec_email = one["email"]
                        server.sendmail(from_email, rec_email, text)
                        print(f"Email sent to user {rec_user} at {rec_email}")
                        time.sleep(1)

        shutil.rmtree(temp_dir)

    except ClientError as e:
        code = e.response['Error']['Code']
        if  code == "UsernameExistsException":
            print(f"ERROR: user {username} already exists.")
        elif code == "InvalidPasswordException":
            print(f"ERROR: password invalid. Please delete user and try again.")
        else:
            print(f"ERROR: {str(e)}")
    except Exception as e:
        print(f"ERROR: can not send invite. {str(e)}")
        exit(1)
    finally:
        if server:
            server.quit()

#
# NOTE: for joining, we don't need the --team parameter specified.
#

@team.command()
@click.option("--invite", help="JSON invitation file", type=click.Path(exists=True), required=True)
@click.option("--key", "-key", help="Invite Decode key")
@click.option("--password", "-pass", help="New account password")
@click.option("--alias", "-as", help="Invite Team name override")
def join(invite, key, password, alias):
    """
    Join an existing team, given invite credentials.
    \f
    This command lets the user join a specific team by downloading the
    credentials necessary to remotely interact with projects, models, etc.

    Byt the time this invite has been sent, the user will have been created
    (if in Cognito) and/or added to the Group in SSO.

    Joining will create a local config file with enough info to let the user
    run CLI operations. To be able to do GUI stuff, they need to login with
    the credentials inside the file (username/temp password).

    At this point we're not doing fine-grain access control, but leaving room to
    enable access only to specific projects.

    :param config:
    :param invite: JSON invitation file sent by the administrator.
    :param alias: instead of the team in the invite, let's join under a different team name.
    :return:

    Examples:
    \b
    $ iot team join --invite myinvite.json

    """
    try:
        invite_text = None
        username = None
        temp_password = None

        with open(invite, "r", encoding='utf-8') as infile:
            invite_text = infile.read()

        if not invite_text:
            print(f"ERROR reading invite file: {invite}")
            exit(1)

        while not key:
            key = questionary.password(f"Enter invite key:").ask()
            if not key:
                print("Please enter the invite key from your invitation message")

        # Make sure we strip out any extra quotes from the ends
        key = unquote(key)

        invite_data_json = _decrypt_invite(key, invite_text)
        invite_data = json.loads(invite_data_json)

        # Invites only work for non-SSO teams. For SSO we assume they have their own
        # invitation mechanism and workflow.
        #
        use_sso = invite_data.get("use_sso", None)
        if not use_sso:
            #
            # We load up the username to cache, but we don't want to save it to the
            # config file. However, we give the user a chance to log in with these credentials.
            # NOTE: we're only using admin login for now. This is in place when we switch over to
            # multi-user support.
            #
            username = invite_data.get("username", None)

        if alias:
            team = alias
        else:
            team = invite_data.get("team", None)

        if team:
            if does_team_exist(team):
                print(f"ERROR: team '{team} already exists on your system.\n       Try adding '--alias={{team-name}}' to choose a different name.")
                exit(1)

            proceed = questionary.confirm(f"Would you like to join the SimpleIOT team [{team}]? ").ask()
            if proceed:
                # Ask for password (using questionary) if not set
                temp_password = invite_data.get("temp_password", None)
                while not password:
                    password = questionary.password(f"New Password:").ask()
                    if not password:
                        print("Please enter password")

                # We remove the username and temporary password from the invite. No need to store it
                # permanently.
                #
                del invite_data['username']
                del invite_data['temp_password']

                config_path = path_for_config_file(team)
                config_data_str = json.dumps(invite_data, indent=4)
                with open(config_path, 'w', encoding='utf-8') as configfile:
                    configfile.write(config_data_str)

                #
                # Now we do the password reset flow using Cognito
                #
                region = invite_data.get("region", None)
                client_id = invite_data.get("cognitoClientId", None)
                if region and client_id:
                    cognito = boto3.client('cognito-idp', region_name=region)
                    response = cognito.initiate_auth(
                        ClientId=client_id,
                        AuthFlow='USER_PASSWORD_AUTH',
                        AuthParameters={
                            'USERNAME': username,
                            'PASSWORD': temp_password
                        }
                    )
                    user_pool_id = invite_data.get('cognitoUserPoolId', None)
                    challenge = response.get("ChallengeName", None)
                    if challenge == "NEW_PASSWORD_REQUIRED":
                        password = unquote(password)
                        challenge_response = cognito.respond_to_auth_challenge(
                            ClientId=client_id,
                            ChallengeName=response['ChallengeName'],
                            Session=response['Session'],
                            ChallengeResponses={
                                'USERNAME': username,
                                'NEW_PASSWORD': password
                            }
                        )
                    else:
                        print(f"Password for user {username} has already been changed.")
                        return

                print("SIMPLEIOT: Team Added.")
                print(" - Make sure you set an environment variable for IOT_TEAM")
                print("   Then visit dashboard in browser or 'iot auth login' in console to login")
                print(f"     with your username: {username} and chosen password.")
                dashboard = invite_data.get("dashboard_url", None)
                table = Table(show_header=True, header_style="green")
                table.add_column("Name", style="dim", overflow="flow")
                table.add_column("Value", style="dim", overflow="flow")
                table.add_row("Dashboard", dashboard)
                if not use_sso:
                    table.add_row("Username", username)

                console.print(table)
        else:
            print(f"ERROR: no team specified")
            exit(1)

    except Exception as e:
        print(f"ERROR: could not load invite data from[{invite}]: {str(e)}")
        exit(1)


@team.command()
@common_cli_params
@click.option("--username", "-user", help="Username", required=True)
def leave(team, profile, username):
    """
    Deletes a user's login credential.
    """
    try:
        config = preload_config(team, profile)
        cognito = None
        account = _is_admin(config)
        if not account:
            print("ERROR: users can only be managed by the administrator.")

        if not ask_to_confirm_yesno("Are you sure you want to delete this user"):
            return

        team = config.team
        if team:
            bootstrap = load_bootstrap_config(team)
            if bootstrap:
                account = bootstrap.get("account", None)
                if not account:
                    print("ERROR: invites can only be sent out by the administrator.")
                    exit(1)
                else:
                    local_config = load_config(team)
                    _remove_user(config, local_config, team, username)
                    # If it fails, it will throw an exception that will be caught later
                print(f"Done: user {username} deleted.")
            else:
                print("ERROR: users can only be delete by the administrator.")
                exit(1)
        else:
            print("ERROR: no team specified")
            exit(1)

    except ClientError as e:
        code = e.response['Error']['Code']
        if code == "UserNotFoundException":
            print(f"ERROR: user {username} not found.")
        else:
            print(f"ERROR: {str(e)}")
    except Exception as e:
        print(f"ERROR: can not delete user. {str(e)}")
        exit(1)


# If it fails, it will throw an exception that will be caught later
#
def _remove_user(config, local_config, team, username):
    use_sso = local_config.get("use_sso", False)
    if not use_sso:
        region = local_config.get("region", None)
        user_pool_id = local_config.get("cognitoUserPoolId", None)
        profile = local_config.get("aws_profile", "default")
        os.environ['AWS_PROFILE'] = profile
        cognito = boto3.client('cognito-idp', region_name=region)
        response = cognito.admin_delete_user(
            UserPoolId=user_pool_id,
            Username=username)


#
# We use this to encrypt the invite payload and turn it into BASE64 text. The invite
# text and the resulting 'key' are then returned. The user should be sent both the invite file
# as well as the key. When they go to join, they will be entering the path to the invite as well
# as the 'key' text. This decrypts the payload, loads what's needed, and prompts the user to enter
# their own unique password for their account.
#
def _encrypt_invite(payload_json):
    try:
        key = Fernet.generate_key()
        f = Fernet(key)
        json_str = json.dumps(payload_json)
        encrypted_payload = f.encrypt(json_str.encode('utf-8'))
        b64_encrypted_payload = base64.standard_b64encode(encrypted_payload).decode('utf-8')
        b64_key = base64.standard_b64encode(key).decode('utf-8')
        return b64_key, b64_encrypted_payload
    except Exception as e:
        print(f"Error encrypting invite: {str(e)}")
        exit(1)


def _decrypt_invite(b64_key, b64_encrypted_payload_str):
    try:
        keyb = b64_key.encode('utf-8')
        key = base64.standard_b64decode(keyb)
        f = Fernet(key)
        b64_encrypted_payload = base64.standard_b64decode(b64_encrypted_payload_str)
        payload = f.decrypt(b64_encrypted_payload)
        return payload
    except Exception as e:
        print(f"Error decrypting invite: {str(e)}")
        exit(1)


def _is_admin(config):
    response = None
    try:
        team = config.team
        if team:
            bootstrap = load_bootstrap_config(team)
            if bootstrap:
                account = bootstrap.get("account", None)
                if account:
                    response = account
    except Exception as e:
        pass

    return response
