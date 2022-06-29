#!/usr/bin/env python

# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
try:
    import boto3
    from botocore.exceptions import ClientError
    from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
except Exception as e:
    print("ERROR: Have you installed from dist or run 'source venv/bin/activate' to initialize dev environment?")
    exit(1)

import datetime
import json
import sys
import signal
import time
import requests
from requests.exceptions import RequestException
from rich import print
from rich.table import Table
import arrow
import stat
import string
import random
import os
from .config import *

#
# This needs to change so it uses different parameters depending on whether the
# back-end support COGNITO authentication or IAM auth (when SSO is used).
#
def make_api_request(method, config, command, **kwargs):
    """Makes API request and handles connection errors"""
    try:
        url = f"{config.api_endpoint}v1/{command}"

        if config.use_sso:
            access_key = get_stored_access_key(config)
            secret_key = get_stored_access_secret(config)
            session_token = get_stored_session_token(config)
            api_endpoint = config.api_endpoint
            region = config.region

            from requests_aws4auth import AWS4Auth
            auth = AWS4Auth(access_key, secret_key, region, 'execute-api',
                            session_token=session_token)

            response = requests.request(method, url, auth=auth, **kwargs)
        else:

            token = get_stored_api_token(config)
            if not token:
                print("ERROR: not logged in. Please run 'iot auth login' to login first.")
                exit(1)

            headers = {
                "Authorization": token
            }

            response = requests.request(method, url, headers=headers, **kwargs)

        if response.status_code != requests.codes.ok and \
           response.status_code != requests.codes.created:
            if response.status_code == requests.codes.unauthorized:
                print("ERROR. Unauthorized. Make sure you have logged-in.")
                exit(1)
            elif response.status_code == requests.codes.forbidden:
                print("ERROR: Request Forbidden. Username does not have permission.")
                print(response.json()['message'])
                exit(1)
            elif response.status_code != 418:
                try:
                    message = response.json()['message']
                    print(f"ERROR: {message}")
                except:
                    print(response.text,
                          '(HTTP error ' + str(response.status_code) + ')')
                    exit()
        return response
    except RequestException as error:
        print('[ Error connecting to the CLI API server:', config.api_endpoint, \
              ']',
              '(' + str(error) + ')')
        exit()


def show_detail(console, name, data):
    table = Table(show_header=True, header_style="green")
    table.add_column("Key", style="dim", overflow="flow")
    table.add_column("Value")
    for key, value in data.items():
        if isinstance(value, list):
            try:
                json_value = json.dumps(value, indent=2)
                value = json_value
            except:
                value = ", ".join(value)
        table.add_row(key, str(value))
    console.print(table)


def write_qr_file(base, prefix, suffix, data):
    import pyqrcodeng
    try:
        if data:
            qr = pyqrcodeng.create(data)
            filename = f"{prefix}_{suffix}.png"
            pngfile = os.path.join(base, filename)
            qr.png(pngfile, scale=5)
    except Exception as e:
        print(
            f"ERROR: unable to save QRCode data for {prefix} to {base} directory. Please fix problem and try again.")

def format_date(dt):
    try:
        arrow_date = arrow.get(dt)
        # result = arrow_date.humanize(granularity=["day", "hour", "minute"])
        result = arrow_date.humanize()
        return result
    except:
        return dt

#
# This is used to get a secret out of secretsmanager.
#
def get_secret(config, name):
    profile = config.get("aws_profile", "default")
    os.environ['AWS_PROFILE'] = profile
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=config.get("region", None)
    )

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

    try:
        secret_value = client.get_secret_value(
            SecretId=name
        )
    except ClientError as e:
        print(f"Got exception: {str(e)}")

        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in secret_value:
            secret = secret_value["SecretString"]
            return json.loads(secret)
        else:
            return None

#
# This is used to subscribe to an MQTT topic. Note that it isn't at all re-entrant, since it
# is meant to be used by a single command at a time. If you need to monitor multiple topics,
# open a new window and start a new shell process.
#
mqtt_client = None
on_data_callback = None
on_error_callback = None
show_raw = False
stop_after_one = False
mqtt_topic = None


def get_device_cert_path(team, project, model, serial, suffix):
    try:
        device_dir = get_iot_device_dir(team, project, model, serial)

        filename = f"{serial}_{suffix}.pem"
        filepath = os.path.join(device_dir, filename)
        return filepath

    except Exception as e:
        print(
            f"ERROR: unable to read device data for {serial} to {base} directory. Please delete device, fix problem, and try again")


def _get_monitor_cert_paths(team):
    ca_file_path = None
    cert_file_path = None
    public_key_file_path = None
    private_key_file_path = None

    try:
        config = load_config(team)
        if config:
            iot_monitor_rootca_filename = config.get("iot_monitor_rootca_filename", None)
            iot_monitor_cert_filename = config.get("iot_monitor_cert_filename", None)
            iot_monitor_public_key_filename = config.get("iot_monitor_public_key_filename", None)
            iot_monitor_private_key_filename = config.get("iot_monitor_private_key_filename", None)

            cert_path = path_for_certs(team)

            ca_file_path = os.path.join(cert_path, iot_monitor_rootca_filename)
            cert_file_path = os.path.join(cert_path, iot_monitor_cert_filename)
            public_key_file_path = os.path.join(cert_path, iot_monitor_public_key_filename)
            private_key_file_path = os.path.join(cert_path, iot_monitor_private_key_filename)
        else:
            print(f"ERROR: failed to load config data for team [ {team} ]")

        return ca_file_path, cert_file_path, public_key_file_path, private_key_file_path

    except Exception as e:
        print(
            f"ERROR: unable to read device data for {serial} to {base} directory. Please delete device, fix problem, and try again")


def _mqtt_callback(client=None, userdata=None, message=None):
    global mqtt_client, on_data_callback, on_error_callback, show_raw, stop_after_one
    try:
        if message:
            topic = message.topic
            payload_str = message.payload
            payload = json.loads(payload_str)
            if on_data_callback:
                result = on_data_callback(topic, payload, show_raw, stop_after_one)
                if not result:
                    #
                    # This kills the whole process group. A regular sys.exit(0) just kills the single thread.
                    #
                    os.kill(os.getpid(), signal.SIGINT)
                    #
                    # For Windows, we may want to call os._exit()
    except Exception as e:
        if on_error_callback:
            on_error_callback(str(e))


def _mqtt_onconnect(client=None, userdata=None):
    global mqtt_client, mqtt_topic

    # print(f"Connected. Subscribing {mqtt_client} to topic: {mqtt_topic}")
    mqtt_client.subscribe(mqtt_topic, 1, _mqtt_callback)
    print(f"Ready.")


def subscribe_to_mqtt_topic(team, project, model, serial, topic,
                            raw=False, stop=False,
                            on_data=None, on_error=None):
    global mqtt_client, on_data_callback, on_error_callback, show_raw, stop_after_one, mqtt_topic

    show_raw = raw
    stop_after_one = stop
    mqtt_topic = topic

    config = load_config(team)
    mqtt_port = config.get("mqtt_port", 8883)
    iot_endpoint = config.get("iot_endpoint", None)
    if not iot_endpoint:
        print(f"ERROR: iot_endpoint not defined. Something may have gone wrong during installation.")
        exit(1)


    # Now we look for the certs for this specific device. If not found, we use the
    # Monitor certs installed at time of
    ca_file_path = get_device_cert_path(team, project, model, serial, "rootca")
    private_key_file_path = get_device_cert_path(team, project, model, serial, "private")
    cert_file_path = get_device_cert_path(team, project, model, serial, "cert")

    if not (ca_file_path or private_key_file_path or cert_file_path):
        ca_file_path, cert_file_path, public_key_file_path, private_key_file_path = _get_monitor_cert_paths(team)

    # let's make a random client ID
    #
    alphabet = string.ascii_lowercase + string.digits
    uuid_str = ''.join(random.choices(alphabet, k=8))
    client_id = f"iot-cli-{uuid_str}"

    if not mqtt_client:
        mqtt_client = AWSIoTMQTTClient(client_id)
        mqtt_client.configureEndpoint(iot_endpoint, mqtt_port)
        mqtt_client.configureCredentials(ca_file_path, private_key_file_path, cert_file_path)
        mqtt_client.configureAutoReconnectBackoffTime(1, 32, 20)
        mqtt_client.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
        mqtt_client.configureDrainingFrequency(2)  # Draining: 2 Hz
        mqtt_client.configureConnectDisconnectTimeout(10)  # 10 sec
        mqtt_client.configureMQTTOperationTimeout(30)  # 30 sec
        # This is our private internal callback. We use it to watch for data, then process the
        # payload before sending it back up.
        #
        mqtt_client.onMessage = _mqtt_callback
        # mqtt_client.onOnline = _mqtt_onconnect
        on_data_callback = on_data        # we save the callback handlers passed down to us
        on_error_callback = on_error

        # Now we go connect. When actually connected, the onOnline handler is called.
        # There we can subscribe to the topic we're interested in.
        #
        mqtt_client.connectAsync(ackCallback=my_connack_callback)
        loopCount = 0
        while True:
            loopCount += 1
            time.sleep(1)

def my_connack_callback(mid, data):
    print(f"Connected to AWS IOT")
    _mqtt_onconnect(None, None)