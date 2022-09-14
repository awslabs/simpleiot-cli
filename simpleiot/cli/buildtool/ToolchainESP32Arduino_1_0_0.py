# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
# This is the base class for toolchain installer/uninstallers. Derived classes
# will then provide ways to install toolchains in a way that can be invoked by
# the firmware to compile and flash a device.
#
# We could have implemented this as a config file, but some toolchains require
# checking for conditions, so having it be done in code would allow inclusion
# of code to make sure everything is set up as needed.
#
from .toolchain import Toolchain
from .toolchainbase import ToolchainLocation, ToolChainBase, ToolchainLocation
from simpleiot.common.utils import *
from simpleiot.common.config import *
import os
from pathlib import Path
import platform
import traceback

ARDUINO_TOOLCHAIN_CONFIG = "~/Library/Arduino15/arduino-cli.yaml"


class ToolchainESP32Arduino_1_0_0(ToolChainBase):
    def __init__(self, default_version):
        version_list = self.get_installed_toolchain_version()

        # If not found, we default to the highest known version.
        if not version_list:
            version_list = default_version

        super(ToolchainESP32Arduino_1_0_0, self).__init__(
            "esp32arloc",
            "Espressif Esp32 Arduino Local",
            "Local Arduino-CLI install for ESP32 ArduinoCore",
            "espressif",
            "esp32",
            "arduino",
            version_list)
        opsys = platform.system()
        if opsys == "Darwin":
            self.executable = "arduino-cli"
        elif opsys == "Windows":
            self.executable = "arduino-cli.exe"
        elif opsys == "Linux":
            self.executable = "arduino-cli"
        else:
            print(f"ERROR: operating system not supported")
            exit(1)


    def install_windows(self, base=Toolchain.base(), location=ToolchainLocation.LOCAL, verbose=False):
        try:
            self.location = location
            if location == ToolchainLocation.LOCAL:
                print(f"Local install {self.name} - {self.desc} for Windows")
                source_path = "https://downloads.arduino.cc/arduino-cli/arduino-cli_latest_Windows_64bit.zip"
                temp_path = Path(tempfile.mkdtemp())
                zip_file = "arduino-cli.zip"
                install_exe = self.exec_path(base)
                download_path = temp_path / zip_file

                exec_command = "powershell Set-PSDebug -Trace 0 &" \
                               f"powershell 'If (Test-Path -Path \"{install_exe}\") {{ Remove-Item -Path \"{install_exe}\" -Force }}' &" \
                               f"cd {temp_path} & " \
                               f"powershell Invoke-WebRequest \"{source_path}\" -OutFile \"{download_path}\" & "\
                               f"powershell -NoLogo -NoProfile -Command Expand-Archive \"{zip_file}\" & "\
                               f"powershell Move-Item arduino-cli/arduino-cli.exe \"{install_exe}\" -Force"
                self._exec(exec_command)
                print(f"Done.")
            else:
                print(f"ERROR: non-local toolchains not supported.")
                exit(1)

        except Exception as e:
            print(f"ERROR: could not install arduino-cli: {str(e)}")
            exit(1)

    # For Mac,we can use Homebrew, but then we can't install multiple versions of toolchain on a single
    # system. For Arduino, we can use the install script and install it in separate directories.
    #
    def install_mac_with_brew(self, base=Toolchain.base(), location=ToolchainLocation.LOCAL, verbose=False):
        try:
            self.location = location
            if location == ToolchainLocation.LOCAL:
                print(f"Local install {self.name} - {self.desc} for Mac")
                if not self._app_exists("arduino-cli"):
                    if self._app_exists("brew"):
                        self._exec("brew install arduino-cli")
                    else:
                        print("ERROR: Homebrew (https://brew.sh/) has to be installed.")
                        exit(1)

                if not self._file_exists("~/Library/Arduino15/arduino-cli.yaml"):
                    self._exec("arduino-cli config init --overwrite")

                self.reset_mac(location=location)
            else:
                print(f"ERROR: non-local toolchains not supported.")
                exit(1)

        except Exception as e:
            print(f"ERROR: could not install toolchain. {str(e)}")
            exit(1)

    def install_mac(self, base=Toolchain.base(), location=ToolchainLocation.LOCAL, verbose=False):
        try:
            self.location = location
            if location == ToolchainLocation.LOCAL:
                print(f"Local install {self.name} - {self.desc} for Mac")

                if verbose:
                    print(f"+ Getting install path for base: {base}")
                install_exe = self.exec_path(base)
                if verbose:
                    print(f"+ Install path: {install_exe}")
                if self._file_exists(install_exe):
                    if verbose:
                        print(f"+ File already exists: {install_exe}")
                    print(f"ERROR: Toolchain app already exists at path: {install_exe}")
                    exit(1)
                else:
                    install_cmd = f"curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR={base} sh"
                    if verbose:
                        print(f"+ Download and install cmd:\n [ {install_cmd} ] in base: {base}\n\n")
                    self._exec(install_cmd)
                    if verbose:
                        print(f"+ Toolchain downloaded and installed")
            else:
                print(f"ERROR: non-local toolchains not supported.")
                exit(1)
        except Exception as e:
            print(f"ERROR: could not install toolchain. {str(e)}")
            exit(1)

    def uninstall_windows(self, base=Toolchain.base(), location=ToolchainLocation.LOCAL, verbose=False):
        try:
            if location == ToolchainLocation.LOCAL:
                print(f"Local uninstall {self.name} - {self.desc} for Windows")

                install_exe = self.exec_path(base)
                delete_command = "powershell Set-PSDebug -Trace 0 &" \
                                 f"powershell 'If (Test-Path -Path \"{install_exe}\") {{ Remove-Item -Path \"{install_exe}\" -Force }}' &"\
                                 f"powershell 'If (Test-Path -Path \"{base}\") {{ Remove-Item -Path \"{base}\" -Force }}'"

                self._exec(delete_command)
                print(f"File {base} removed.")
            else:
                print(f"ERROR: non-local toolchains not supported.")
                exit(1)
        except Exception as e:
            print(f"ERROR uninstalling tool: {str(e)}")
            exit(1)

    def uninstall_mac_with_brew(self, base=Toolchain.base(), location=ToolchainLocation.LOCAL, verbose=False):
        try:
            if location == ToolchainLocation.LOCAL:
                print(f"Local uninstall {self.name} - {self.desc} for Mac")

                if self._app_exists("arduino-cli"):
                    if self._app_exists("brew"):
                        self._exec("brew uninstall arduino-cli --force --quiet")
                    else:
                        print("ERROR: Homebrew (https://brew.sh/) has to be installed.")
                        exit(1)
                else:
                    print(f"ERROR: arduino-cli not found in path")
        except Exception as e:
            print(f"ERROR uninstalling tool: {str(e)}")
            exit(1)

    def uninstall_mac(self, base=Toolchain.base(), location=ToolchainLocation.LOCAL, verbose=False):
        try:
            if location == ToolchainLocation.LOCAL:
                print(f"Local uninstall {self.name} - {self.desc} for Mac")

                install_exe = self.exec_path(base)
                if verbose:
                    print(f"+ Install executable path: {install_exe}")

                if verbose:
                    print(f"+ Check that executable exists...")
                if self._file_exists(install_exe):
                    if verbose:
                        print(f"+ Install executable path: {install_exe}")

                    import shutil
                    shutil.rmtree(base)
                else:
                    print(f"ERROR: toolchain executable not found in path: {install_exe}")
            else:
                print(f"ERROR: non-local toolchains not supported.")
                exit(1)
        except Exception as e:
            print(f"ERROR uninstalling tool: {str(e)}")
            exit(1)


    def reset_windows(self, base=Toolchain.base(), location=ToolchainLocation.LOCAL, verbose=False):
        try:
            if location == ToolchainLocation.LOCAL:
                print(f"Local reset to factory settings for {self.name} for Windows")
                install_exe = self.exec_path(base)

                if self._file_exists(install_exe):
                    self._exec(f"{install_exe} config init --overwrite")
                    self._exec(f"{install_exe} config set board_manager.additional_urls https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json")
                    self._exec(f"{install_exe} config set library.enable_unsafe_install true")
                    self._exec(f"{install_exe} core update-index ")
                    self._exec(f"{install_exe} core install esp32:esp32")
                    self._exec(f"{install_exe} lib install ArduinoJson")
                    self._exec(f"{install_exe} lib install ArduinoMqttClient")
                    self._exec(f"{install_exe} lib install FastLED")
                    self._exec(f"{install_exe} lib install TinyGPSPlus-ESP32")
                    self._exec(f"{install_exe} lib install --git-url https://github.com/m5stack/M5Core2.git")
                    self._exec(f"{install_exe} lib install --git-url https://github.com/m5stack/UNIT_ENV.git")
                    self._exec(f"{install_exe} lib install --git-url https://github.com/m5stack/UNIT_ENCODER.git")
                    self._exec(f"{install_exe} lib install --git-url https://github.com/aws-samples/arduino-aws-greengrass-iot.git")
                    self._exec(f"{install_exe} lib install --git-url https://github.com/awslabs/simpleiot-arduino.git")
                    print("Done: arduino-cli configured")
                else:
                    print(f"Error: arduino-cli not found at {install_exe}")
            else:
                print(f"ERROR: non-local toolchains not supported.")
                exit(1)
        except Exception as e:
            print(f"ERROR resetting tool to factory default: {str(e)}")
            exit(1)


    def reset_mac_with_brew(self, base=Toolchain.base(), location=ToolchainLocation.LOCAL, verbose=False):
        try:
            if location == ToolchainLocation.LOCAL:
                print(f"Local reset to factory-settings for {self.name} for Mac")

                if not self._app_exists("arduino-cli"):
                    print("ERROR: arduino-cli is not installed")
                    exit(1)

                if self._file_exists(ARDUINO_TOOLCHAIN_CONFIG):
                    print(f"WARNING: Arduino toolchain configuration file already exists.")
                    print(f"Please move {ARDUINO_TOOLCHAIN_CONFIG} then re-run install command.")
                    exit(1)

                install_exe = "arduino-cli"

                self._exec(f"{install_exe} config set board_manager.additional_urls https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json")
                self._exec(f"{install_exe} config set library.enable_unsafe_install true")
                self._exec(f"{install_exe} core update-index ")
                self._exec(f"{install_exe} core install esp32:esp32")
                self._exec(f"{install_exe} lib install ArduinoJson")
                self._exec(f"{install_exe} lib install ArduinoMqttClient")
                self._exec(f"{install_exe} lib install FastLED")
                self._exec(f"{install_exe} lib install TinyGPSPlus-ESP32")
                self._exec(f"{install_exe} lib install --git-url https://github.com/m5stack/M5Core2.git")
                self._exec(f"{install_exe} lib install --git-url https://github.com/m5stack/UNIT_ENV.git")
                self._exec(f"{install_exe} lib install --git-url https://github.com/m5stack/UNIT_ENCODER.git")
                self._exec(f"{install_exe} lib install --git-url https://github.com/aws-samples/arduino-aws-greengrass-iot.git")
                self._exec(f"{install_exe} lib install --git-url https://github.com/awslabs/simpleiot-arduino.git")
                print(f"Done: {install_exe} configured")
            else:
                print(f"ERROR: non-local toolchains not supported.")
                exit(1)
        except Exception as e:
            print(f"ERROR: Could not reset {install_exe}: {str(e)}")
            exit(1)

    def reset_mac(self, base=Toolchain.base(), location=ToolchainLocation.LOCAL, verbose=False):
        try:
            if location == ToolchainLocation.LOCAL:
                print(f"Local reset to factory-settings for {self.name} for Mac")

                install_path = self.install_path(base)
                if verbose:
                    print(f"+ Installer path: {install_path} with base: {base}")
                install_exe = self.exec_path(install_path)
                if verbose:
                    print(f"+ Install executable: {install_exe}")
                    print(f"+ Check if exists...")

                if install_exe.exists():
                    if verbose:
                        print(f"+ Executable exists. Checking toolchain config at: {ARDUINO_TOOLCHAIN_CONFIG}")

                    if not self._file_exists(ARDUINO_TOOLCHAIN_CONFIG):
                        if verbose:
                            print(f"+ Arduino Toolchain config does not exist. Running init to create basic skeleton.")

                        cmd = f"{install_exe} config init --overwrite"
                        if verbose:
                            print(f" + Invoking: {cmd}")
                        self._exec(cmd)

                    cmd = f"{install_exe} config set board_manager.additional_urls https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json"
                    if verbose:
                        print(f" + Exec: {cmd}")
                    self._exec(cmd)

                    cmd = f"{install_exe} config set library.enable_unsafe_install true"
                    if verbose:
                        print(f" + Exec: {cmd}")
                    self._exec(cmd)

                    cmd = f"{install_exe} core update-index"
                    if verbose:
                        print(f" + Exec: {cmd}")
                    self._exec(cmd)

                    cmd = f"{install_exe} core install esp32:esp32"
                    if verbose:
                        print(f" + Exec: {cmd}")
                    self._exec(cmd)

                    cmd = f"{install_exe} lib install ArduinoJson"
                    if verbose:
                        print(f" + Exec: {cmd}")
                    self._exec(cmd)

                    cmd = f"{install_exe} lib install ArduinoMqttClient"
                    if verbose:
                        print(f" + Exec: {cmd}")
                    self._exec(cmd)

                    cmd = f"{install_exe} lib install FastLED"
                    if verbose:
                        print(f" + Exec: {cmd}")
                    self._exec(cmd)

                    cmd = f"{install_exe} lib install TinyGPSPlus-ESP32"
                    if verbose:
                        print(f" + Exec: {cmd}")
                    self._exec(cmd)

                    cmd = f"{install_exe} lib install --git-url https://github.com/m5stack/M5Core2.git"
                    if verbose:
                        print(f" + Exec: {cmd}")
                    self._exec(cmd)

                    cmd = f"{install_exe} lib install --git-url https://github.com/m5stack/UNIT_ENV.git"
                    if verbose:
                        print(f" + Exec: {cmd}")
                    self._exec(cmd)

                    cmd = f"{install_exe} lib install --git-url https://github.com/m5stack/UNIT_ENCODER.git"
                    if verbose:
                        print(f" + Exec: {cmd}")
                    self._exec(cmd)

                    cmd = f"{install_exe} lib install --git-url https://github.com/aws-samples/arduino-aws-greengrass-iot.git"
                    if verbose:
                        print(f" + Exec: {cmd}")
                    self._exec(cmd)

                    cmd = f"{install_exe} lib install --git-url https://github.com/awslabs/simpleiot-arduino.git"
                    if verbose:
                        print(f" + Exec: {cmd}")
                    self._exec(cmd)

                    print(f"Done: {install_exe} configured")
                else:
                    print(f"ERROR: build tool not found in local path: {base}.\nPlease uninstall then re-install.")
                    exit(1)

            else:
                print(f"ERROR: non-local toolchains not supported.")
                exit(1)
        except Exception as e:
            print(f"ERROR: Could not reset {install_exe}: {str(e)}")
            traceback.print_exc()
            exit(1)

    #
    # Parameters will be passed to compiler and flash tool
    #
    def build(self, base, dirpath, command, verbose=False):
        exec = self.exec_path(base)
        full_command = f"{exec} {command}"
        os.chdir(dirpath)
        print(f"DIR: {dirpath}")
        print(f"EXECUTING: {full_command}")
        self._invoke_unbuffered(full_command)
        return True

    def flash(self, base, dirpath, command, verbose=False):
        exec = self.exec_path(base)
        full_command = f"{exec} {command}"
        print(f"DIR: {dirpath}")
        print(f"EXECUTING: {full_command}")
        os.chdir(dirpath)
        self._invoke_unbuffered(full_command)
        return True

    def build_and_flash(self, base, dirpath, command, verbose=False):
        install_path = self.install_path(base)
        exec = self.exec_path(install_path)
        full_command = f"{exec} {command}"
        # print(f"DIR: {dirpath}")
        # print(f"EXECUTING: {full_command}")
        # self._invoke_unbuffered(full_command)
        self._exec(full_command)
        return True


    # This method looks for the local toolchain installation. If it's there, it returns it.
    # Note that this may be different than the version returned by the tool itself.
    # We need this version so at runtime, the flasher tool can be located.
    # Each platform will have a different way of determining it.
    # If the tool hasn't been installed yet, we just return "***".
    #
    def get_installed_toolchain_version(self, install_path=None):
        result = None
        try:
            import glob
            tool_path = None

            opsys = platform.system()
            if opsys == "Darwin":
                tool_path = glob.glob(os.path.expanduser("~/Library/Arduino15/**/esptool"), recursive=True)
            elif opsys == "Windows":
                tool_path = glob.glob(os.path.expanduser("~\\AppData\\Local\\Arduino15\\**\\esptool.exe"),
                                      recursive=True)

            version_list = []
            if tool_path:
                for one in tool_path:
                    one_list = one.split(os.sep)
                    version = one_list[-2]
                    version_list.append(version)
                result = ", ".join(version_list)
            return result
        except Exception as e:
            print(f"ERROR flashing device: {str(e)}")

