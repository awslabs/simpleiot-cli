# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
# iot firmware -- can be used to:
#    generate: creates templatized code for building firmware
#    build: compile code and build binary (you can pass the wifi ssid info to it)
#    flash: flash binary to device via USB
#
#!/usr/bin/env python

import click
from simpleiot.common.utils import *
from simpleiot.common.config import *

from rich import print
from rich.console import Console
from rich.table import Table
import serial.tools.list_ports
import questionary
import tempfile
import os as ops
import inspect
import zipfile
from pathlib import Path
from shutil import which
import requests
import platform
from simpleiot.cli.buildtool.toolchain import Toolchain
from simpleiot.cli.toolchain import  LATEST_ARDUINO_ESP32_TOOLCHAIN_VERSION

#######################

console = Console()


@click.group()
def firmware():
    """Generate sample source"""


@firmware.command()
@common_cli_params
@click.option("--project", help="Project name", envvar="IOT_PROJECT")
@click.option("--serial", help="Device serial", envvar="IOT_DEVICE")
@click.option("--manufacturer", "--brand", help="Manufacturer name", default="espressif")
@click.option("--processor", "--cpu", help="Processor type", default="esp32")
@click.option("--os", help="Operating system name", default="arduino")
@click.option("--name", help="Generator name", required=True)
@click.option("--version", help="Firmware version", default=LATEST_ARDUINO_ESP32_TOOLCHAIN_VERSION)
@click.option("--wifi_ssid", "--ssid", help="Wifi SSID name", envvar="IOT_WIFI_SSID")
@click.option("--wifi_password", "--password", help="Wifi Password", envvar="IOT_WIFI_PASSWORD")
def generate(team, profile, project, serial, manufacturer, processor, os, name,
             version, wifi_ssid, wifi_password):
    """Generates firmware source
    \f
    Given a defined manufacturer, processor, and OS, generate firmware source that can be compiled
    and uploaded to a device. If the WiFi SSID/Password are specified, they are added to the
    source file.

    \b
    $ iot firmware generate --project=... --serial=... --os=...

    The return data is a .ZIP file with the code.
    """
    try:
        config = preload_config(team, profile)

        show_all = False

        payload = {}
        multi = True

        if project:
            payload["project_name"] = project
        if serial:
            payload["serial"] = serial
        if manufacturer:
            payload["manufacturer"] = manufacturer
        if processor:
            payload["processor"] = processor
        if os:
            payload["os"] = os
        if name:
            payload["generator_name"] = name
        if version:
            payload["version"] = version
        if wifi_ssid:
            payload["wifi_ssid"] = wifi_ssid
        if wifi_password:
            payload["wifi_password"] = wifi_password

        # If no project specified, we show a list
        #
        if not project:
            show_all = True

        if show_all:
            response = make_api_request("GET", config, "firmware")
        else:
            response = make_api_request("POST", config, "firmware", json=payload, stream=True)

        if response.status_code == requests.codes.ok:
            content_type = response.headers['content-type']
            if content_type == 'application/zip':
                content_disp = response.headers['content-disposition']
                filename = re.findall("filename=(.+)", content_disp)[0]

                with open(filename, 'wb') as output:
                    shutil.copyfileobj(response.raw, output)
                del response
                print(f"Done. Code generated into: {filename}")
            else:
                data = response.json()
                table = Table(show_header=True, header_style="green")
                table.add_column("Generator")
                table.add_column("Manufacturer")
                table.add_column("Processor")
                table.add_column("OS")
                table.add_column("File")
                table.add_column("Date Created", justify="right")
                for d in data:
                    name = d.get("name", "***")
                    manufacturer = d.get("manufacturer", "***")
                    processor = d.get("processor", "***")
                    os = d.get("os", "***")
                    zip_url = d.get("zip_url", "***")
                    filename = zip_url.rsplit('/', 1)[1]
                    created = d.get("date_created", "***")
                    table.add_row(name, manufacturer, processor, os, filename, format_date(created))

                console.print(table)
        else:
            data = response.json()
            status = data.get("status", "***")
            message = data.get("message", "***")
            table = Table(show_header=True, header_style="red")
            table.add_column("Generator List Status")
            table.add_column("Message")
            table.add_row(status, message)

            console.print(table)
    except Exception as e:
        print(f"ERROR: {str(e)}")


# These are hard-coded for the demo device (M5Stack Core2). Add device VID/PID
# if not recognized or they change their chipset. Run 'lsusb' and add the
# hex value of the USB port into the array below.
#
# NOTE that the fqbn is hard-coded for the M5Stack EduKit device. For other devices,
# you'll need to change this. To get the list of all supported boards, run:
#
#    arduino-cli board listall
#
# The FQBN is listed next to the name, if the board support package is installed for it:
# To get details on the board:
#
#    arduino-cli board details {board-fqbn}
#
# More info here: https://forum.arduino.cc/t/finding-a-fqbn-for-a-device-that-doesnt-come-up-on-board-list/676662
#
FILTER_VID = [0x1a86, 0x10c4]
FILTER_PID = [0x55d4, 0xea60]
FQBN="esp32:esp32:m5stack-core2"

@firmware.command()
@click.option("--base", "--path", help="Base path of toolchain", default=Toolchain.base())
@click.option("--manufacturer", "--brand", help="Manufacturer name", default="espressif")
@click.option("--processor", "--cpu", help="Processor type", default="esp32")
@click.option("--os", help="Operating system name", default="arduino")
@click.option("--version", help="Firmware version", default=LATEST_ARDUINO_ESP32_TOOLCHAIN_VERSION)
@click.option("--location", help="Install location type",
              type=click.Choice(["local", "local_container", "cloud_container", "cloud_server"], case_sensitive=False),
              default="local")
@click.option("--zip", help="Source zip file")
@click.option("--dir", help="Source directory")
@click.option("--port", help="Serial port to flash device")
def flash(base, manufacturer, processor, os, version, location, zip, dir, port):
    """Build and flash firmware to device
    """
    try:

        # port = "/dev/cu.usbserial-01F9734D"
        port = get_port(port)
        source_dir = None
        clean_on_exit = False

        if not port:
            print(f"ERROR: no --port specified")
            exit(1)

        if zip:
            # Note: in python 3.10, there was an ignore_cleanup_errors parameter added.
            # Once we move the minimum python requirement to 3.10, we can add this to the
            # following constructor.
            # Details: https://docs.python.org/3/library/tempfile.html#tempfile.TemporaryDirectory
            #
            source_dir = tempfile.mkdtemp(prefix="iot")
            # source_dir = source_temp_dir.name
            with zipfile.ZipFile(zip, "r") as zip_file:
                zip_file.extractall(source_dir)
            clean_on_exit = True

        # If they've passed along a directory name instead of a zip file...
        if dir:
            if ops.path.exists(dir):
                source_dir = dir

        # Let's find the sketch_name. Under Arduino, the directory name and the .ino file must match.
        #
        if source_dir:
            directories = ops.scandir(source_dir)
            sketch_name = None
            for entry in directories:
                if entry.is_dir():
                    sketch_name = entry.name
                    break

            if sketch_name:
                sketch_dir = Path(ops.path.join(source_dir, sketch_name))
                # print(f"SKETCH DIR: {sketch_dir}")

                from yaspin import yaspin

                with yaspin(text="Building and Flashing... ", color="green") as spinner:
                    toolchain = Toolchain()
                    command = f"compile -v -u -p {port} --fqbn {FQBN} {sketch_dir}"
                    toolchain.build_and_flash(base, manufacturer, processor, os, version, location, sketch_dir, command)
                    spinner.ok("✅ ")
                    print("Done!")

            else:
                print("ERROR: could not locate sketch root in downloaded project. Invalid template layout.")

        if clean_on_exit:
            import shutil
            # print(f"Cleaning dir: {source_dir}")
            print(f"Cleaning up...")
            shutil.rmtree(source_dir)

    except Exception as e:
        print(f"ERROR flashing device: {str(e)}")



#
# This is hard-set for our demo device, the ESP-32 based M5Stack EduKit. To change it, the various partition sizes
# will need to be calculated and set. This command is here so we can load a very basic animated app onto the device
# after demos. Then when you flash it with a new app, it makes it obvious it's changed.

# NOTE: if we want to re-create the demo, go into Arduino IDE Preferences, and toggle on the 'Show verbose output
# during: compilation' flag. Then build and watch what the command will be for uploading binaries to the device.
# Then replicate those files and that command below. This command is very specific to the M5 Core2 and is here to
# simplify resetting a demo device back into its pre-demo state.
#
# NOTE 2: There is a standalone version of esptool.py on pypi. There was hope that it could be used instead of
# hard-coded/platform specific paths to esptool.py. However, that command did not work when flashing using parameters
# generator by the Arduino toolchain.
#
@firmware.command()
@click.option("--demo", help="Demo directory", default="demo/m5gif")
@click.option("--port", help="Serial port to flash device")
def m5demo(demo, port):
    """Flash a demo Sketch file to the target device.
    """
    try:
        import glob
        from yaspin import yaspin

        tool_path = None

        pkg_dir = Path(ops.path.dirname(ops.path.abspath(inspect.getfile(inspect.currentframe()))))
        demo_path = pkg_dir.parent / demo
        if not ops.path.exists(demo_path):
            print(f"ERROR: could not locate demo directory {demo_path}")
            exit(1)

        opsys = platform.system()
        if opsys == "Darwin":
            tool_path = glob.glob(os.path.expanduser("~/Library/Arduino15/**/esptool"), recursive=True)
        elif opsys == "Windows":
            tool_path = glob.glob(os.path.expanduser("~\\AppData\\Local\\Arduino15\\**\\esptool.exe"), recursive=True)

        if tool_path:
            esptool_path = tool_path[0]
        else:
            print(f"ERROR: could not locate esptool flashing tool. Have you installed the toolchain?")
            exit(1)

        port = get_port(port)
        print(f"Writing via Port: {port}")
        if port:
            if Path(demo_path).is_dir():
                chip = "esp32"
                boot_app0 = demo_path / "boot_app0.bin"
                bootloader = demo_path / "m5gif.ino.bootloader.bin"

                bin_file = demo_path / "m5gif.ino.bin"
                partition_bin_file = demo_path / "m5gif.ino.partitions.bin"

                flash_size = "16MB"
                flash_freq = "80m"
                baud_rate = "921600"

                command = f"{esptool_path} --chip {chip} --port {port} --baud {baud_rate} " \
                          f"--before default_reset --after hard_reset " \
                          f"write_flash " \
                          f"-z --flash_mode dio --flash_freq {flash_freq} " \
                          f"--flash_size {flash_size} " \
                          f"0x1000 {bootloader} " \
                          f"0x8000 {partition_bin_file} " \
                          f"0xe000 {boot_app0} " \
                          f"0x10000 {bin_file}"
                # print(f"Command: {command}")

                with yaspin(text="Flashing... ", color="green") as spinner:
                    ops.system(command)
                    spinner.ok("✅ ")

            print("Done!")

    except Exception as e:
        print(f"ERROR flashing device: {str(e)}")


def get_list_of_serial_ports():
    devices = []
    for item in serial.tools.list_ports.comports():
        # item_json = json.dumps(item.__dict__, indent=2)
        # print(f"Got port: {item_json}")
        if item.vid in FILTER_VID and item.pid in FILTER_PID:
            device = {
                   "name": item.name,
                   "port": item.device
            }
            devices.append(device)
    return devices

#
# If a port has been defined on the command-line we use that. Otherwise we scan for what's available
# on the system and if more than one, we ask the user which one to use.
#
def get_port(port):
    if not port:
        devices = get_list_of_serial_ports()
        if len(devices) == 0:
            print("ERROR: no M5 device found. Please install driver and plug device into USB and try again.")
            exit(1)

        # If we only have one port, we just use it. Otherwise we ask to pick which one to use.
        #
        if len(devices) == 1:
            port = devices[0]['port']
        else:
            device_list = []
            for d in devices:
                device_list.append(d['name'])

            device_name = questionary.select("Choose USB port to use: ", choices=device_list).ask()
            if device_name:
                for dev in devices:
                    if device_name == dev['name']:
                        port = dev['port']
    return port


def does_cli_exist(name):
    opsys = platform.system()
    if opsys == "Darwin":
        cli = which(name)
    elif opsys == "Windows":
        cli = ops.path.expanduser("~\\Downloads\\arduino-cli.exe")
    return cli
