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
from enum import Enum
from shutil import which
import os
import subprocess
import binascii
from pathlib import Path


class ToolchainLocation(Enum):
    LOCAL = 'local'                        # In local filesystem
    CONTAINER = 'container'                # Locally via Docker container
    CLOUD_CONTAINER = 'cloud_container'    # Remote container hosting, connection via API
    CLOUD_SERVICE = 'cloud_service'        # Remote central cloud service, connection via API

    def __getitem__(self, item):
        if isinstance(item, str):
            item = item.lower()
        return super().__getitem__(item)

#####################################################################

class ToolChainBase():
    def __init__(self,
                 alias,
                 name,
                 desc,
                 manufacturer,
                 processor,
                 opsys,
                 version="1.0.0",
                 can_compile=True,
                 can_flash=True,
                 can_compile_and_flash=True,
                 location=ToolchainLocation.LOCAL):
        self.alias = alias
        self.name = name
        self.desc = desc
        self.manufacturer = manufacturer
        self.processor = processor
        self.opsys = opsys
        self.can_compile = can_compile
        self.can_flash = can_flash
        self.can_compile_and_flash = can_compile_and_flash
        self.version = version
        self.location = location
        self.key = self._make_key(manufacturer, processor, opsys, version)
        self.alias_dict = {
            "man": manufacturer,
            "pro": processor,
            "ops": opsys,
            "ver": version,
            "loc": location
        }
        self.executable = ""


    def _make_key(self, manufacturer, processor, opsys, version):
        strkey = f"{manufacturer}::{processor}::{opsys}::{version}"
        hexbin = binascii.hexlify(strkey.encode("utf-8"))
        hexstr = str(hexbin, "utf-8")
        return hexstr

    def _app_exists(self, name):
        """Check whether name is on PATH and marked as executable."""
        return which(name) is not None

    def _file_exists(self, name):
        result = False
        if name:
            expanded_path = os.path.expanduser(name)
            result = os.path.exists(expanded_path)
        return result

    def _exec(self, command):
        x = subprocess.run(command, shell=True, capture_output=True)
        return x
        # return os.system(command)

    def _invoke_unbuffered(self, command):
        try:
            if sys.platform == "win32":
                # For windows we use wexpect
                import msvcrt
                msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
                os.system(command)

            else:
                # For mac or Linux we use pexpect
                import pexpect
                c = pexpect.spawnu(command)
                c.interact()
                c.kill(1)
        except Exception as e:
            pass

    def install_path(self, base):
        if type(base) != Path:
            base = Path(base)
        install_path = Path(os.path.expanduser(base)) / self.key
        if not install_path.exists():
            os.makedirs(install_path)
        return install_path

    def exec_path(self, install_path):
        if type(install_path) != Path:
            install_path = Path(install_path)

        exec_path = install_path / self.executable
        return exec_path

    def get_installed_toolchain_version(self, install_path=None):
        """ Return the version of the installed tool """
        raise NotImplementedError


    # The following may be overridden for each platform.
    #
    def install_windows(self, base, location):
        """ Install this toolchain """
        raise NotImplementedError

    def install_mac(self, base, location):
        """ Install this toolchain """
        raise NotImplementedError

    def install_unix(self, base, location):
        """ Install this toolchain """
        raise NotImplementedError

    def uninstall_windows(self, base, location):
        """ Uninstall this toolchain """
        raise NotImplementedError

    def uninstall_mac(self, base, location):
        """ Uninstall this toolchain """
        raise NotImplementedError

    def uninstall_unix(self, base, location):
        """ Uninstall this toolchain """
        raise NotImplementedError

    def reset_windows(self, base, location):
        """ Reset this toolchain to its original factory settings. """
        raise NotImplementedError

    def reset_mac(self, base, location):
        """ Reset this toolchain to its original factory settings. """
        raise NotImplementedError

    def reset_unix(self, base, location):
        """ Reset this toolchain to its original factory settings. """
        raise NotImplementedError

    #
    # NOTE: this could be expanded to support additional build actions, etc.
    #
    def build(self, base, dirpath, command):
        """ User the tool spec to compile/link the code into binaries """
        raise NotImplementedError

    def flash(self, base, dirpath, command):
        """ User the tool spec to flash the code into binaries """
        raise NotImplementedError

    def build_and_flash(self, base, dirpath, command):
        """ User the tool spec to build and flash the source into binaries """
        raise NotImplementedError
