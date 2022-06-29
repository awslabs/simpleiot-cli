# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
# This is a generic installer for the arduino-cli. It should work on both Mac and Windows
# platforms.
#
import os.path

from invoke import task, Collection
from invoke.executor import Executor
import platform
from shutil import which
import tempfile
import shutil

#
# This installs the arduino-cli
#

@task()
def install(c):
    opsys = platform.system()
    if opsys == "Darwin":
        if not app_exists("arduino-cli"):
            if app_exists("brew"):
                c.run("brew install arduino-cli")
            else:
                print("ERROR: Make sure Homebrew is installed.")
                exit(1)
        pass
    elif opsys == "Windows":
        source_path = "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Windows_64bit.zip"
        temp_path = tempfile.mkdtemp()
        zip_file = "arduino-cli.zip"
        install_dir = "~/Downloads"
        install_exe = f"{install_dir}/arduino-cli.exe"
        print(f"Temp-path: {temp_path}")
        download_path = os.path.join(temp_path, zip_file)
        print(f"Download path: {download_path}")

        c.run(f"cd {temp_path} &"
              f"powershell Remove-Item -Path {install_exe} -Force &"
              f"powershell Invoke-WebRequest {source_path} -OutFile {download_path} &"
              f"powershell -NoLogo -NoProfile -Command Expand-Archive {zip_file} &"
              f"powershell Move-Item arduino-cli/arduino-cli.exe {install_exe}")
        print("Done. Installed in 'Downloads/arduino-cli'")
    elif opsys == "Linux":
        pass


@task()
def uninstall(c):
    opsys = platform.system()
    if opsys == "Darwin":
        if app_exists("arduino-cli"):
            if app_exists("brew"):
                c.run("brew uninstall arduino-cli")
            else:
                print("ERROR: Make sure Homebrew is installed.")
                exit(1)
        pass
    elif opsys == "Windows":
        install_dir = os.path.expanduser("~/Downloads")
        install_exe = f"{install_dir}/arduino-cli.exe"

        if file_exists(install_exe):
            c.run(f"powershell Remove-Item -Path {install_exe} -Force")
            print("Done. Removed from 'Downloads/arduino-cli'")
        else:
            print("Error. arduino-cli not found")
    # elif opsys == "Linux":
    #     pass


@task()
def setup(c):
    opsys = platform.system()
    if opsys == "Darwin":
        if app_exists("arduino-cli"):
            print("Setting up arduino-cli")
    elif opsys == "Windows":
        install_dir = os.path.expanduser("~/Downloads")
        install_exe = f"{install_dir}/arduino-cli.exe"

        if file_exists(install_exe):
            c.run(f"{install_exe} config init --overwrite")
            c.run(f"{install_exe} config set board_manager.additional_urls https://dl.espressif.com/dl/package_esp32_index.json")
            c.run(f"{install_exe} config set library.enable_unsafe_install true")
            c.run(f"{install_exe} core update-index ")
            c.run(f"{install_exe} core install esp32:esp32")
            c.run(f"{install_exe} lib install ArduinoJson")
            c.run(f"{install_exe} lib install MQTT")
            c.run(f"{install_exe} lib install FastLED")
            c.run(f"{install_exe} lib install TinyGPSPlus-ESP32")
            c.run(f"{install_exe} lib install --git-url https://github.com/m5stack/M5Core2.git")
            c.run(f"{install_exe} lib install --git-url https://github.com/m5stack/UNIT_ENV.git")
            c.run(f"{install_exe} lib install --git-url https://github.com/m5stack/UNIT_ENCODER.git")
            c.run(f"{install_exe} lib install --git-url https://github.com/aws-samples/arduino-aws-greengrass-iot.git")
            c.run(f"{install_exe} lib install --zip-path ./simpleiot-arduino.zip")
            print("Done: arduino-cli configured")
        else:
            print(f"Error: arduino-cli not found at {install_exe}")


def app_exists(name):
    """Check whether name is on PATH and marked as executable."""
    return which(name) is not None


def file_exists(name):
    return os.path.exists(name)
