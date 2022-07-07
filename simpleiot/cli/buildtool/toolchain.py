# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#
# Toolchain installer classes
#
import platform
import binascii
import traceback
import sys
import os
import shutil
from pathlib import Path

DEFAULT_TOOLCHAIN_BASE="~/.simpleiot/_toolchain"


class Toolchain:
    toolchain_list = {}
    toolchain_alias = {}

    def __init__(self):
        # NOTE: we import the import of implementation classes here so we don't create import loops.
        # This way, the implementation classes can call class methods without causing import loops.
        #
        from .ToolchainESP32Arduino_1_0_0 import ToolchainESP32Arduino_1_0_0

        self._register(ToolchainESP32Arduino_1_0_0())

        # Add import/list of other toolchains here, for example:
        # self._register("microchip", "imx7", "freertos", "1.0.0", ToolchainIMX7FreeRTOS_1_0_0)

    @classmethod
    def base(cls):
        """
        Returns the default base directory for toolchains. On devices that use external installation
        tools (like Mac with Homebrew) this is ignored.
        """
        return DEFAULT_TOOLCHAIN_BASE

    def _make_key(self, manufacturer, processor, opsys, version):
        strkey = f"{manufacturer}::{processor}::{opsys}::{version}"
        hexbin = binascii.hexlify(strkey.encode("utf-8"))
        hexstr = str(hexbin, "utf-8")
        return hexstr

    # The key and alias_dict are calculated in the constructor
    #
    def _register(self, cls):
        self.toolchain_list[cls.key] = cls
        self.toolchain_alias[cls.alias] = cls.alias_dict

    def _resolve_alias(self, alias):
        cls = self.toolchain_alias.get(alias, None)
        if not cls:
            print(f"ERROR: Toolchain alias '{alias}' not recognized.")
            exit(1)
        return cls

    def _load_config(self):
        print("Load local config file and see what's installed on this machine")

    def _set_config(self, manufacturer, processor, opsys, version, location, binary):
        key = self._make_key(manufacturer, processor, opsys, version)
        print("Save configuration data for this platform -- overwrites old one")

    def _delete_config(self, manufacturer, processor, opsys, version, location, binary):
        key = self._make_key(manufacturer, processor, opsys, version)
        print("Deletes configuration data for this platform--after install")

    def install_alias(self, base, alias):
        params = self._resolve_alias(alias)
        self.install(base,
                     params["man"],
                     params["pro"],
                     params["ops"],
                     params["ver"],
                     params["loc"])


    def install(self, base, manufacturer, processor, opsys, version, location):
        try:
            key = self._make_key(manufacturer, processor, opsys, version)
            installer = self.toolchain_list.get(key, None)
            if installer:
                install_dir = installer.install_path(base)

                opsys = platform.system()
                if opsys == "Darwin":
                    installer.install_mac(install_dir, location)
                elif opsys == "Windows":
                    installer.install_windows(install_dir, location)
                elif opsys == "Linux":
                    installer.install_unix(install_dir, location)
                else:
                    print(f"ERROR: operating system not supported")
            else:
                print(f"ERROR: unable to install toolchain for specified device")
                exit(1)
        except Exception as e:
            print(f"ERROR installing tool: {str(e)}")
            print(traceback.format_exc())
            exit(1)


    def uninstall(self, base, manufacturer, processor, opsys, version, location):
        try:
            key = self._make_key(manufacturer, processor, opsys, version)
            installer = self.toolchain_list.get(key, None)
            if installer:
                install_dir = installer.install_path(base)

                opsys = platform.system()
                if opsys == "Darwin":
                    installer.uninstall_mac(install_dir, location)
                elif opsys == "Windows":
                    installer.uninstall_windows(install_dir, location)
                elif opsys == "Linux":
                    installer.uninstall_unix(install_dir, location)
                else:
                    print(f"ERROR: operating system not supported")

                # Also remove the directory in .simpleiot
                #
                shutil.rmtree(install_dir)
            else:
                print(f"ERROR: unable to uninstall toolchain for specified device")
                exit(1)
        except Exception as e:
            print(f"ERROR uninstalling tool: {str(e)}")
            exit(1)

    def reset(self, base, manufacturer, processor, opsys, version, location):
        try:
            print("Loading defaults for toolchain...")
            key = self._make_key(manufacturer, processor, opsys, version)
            installer = self.toolchain_list.get(key, None)
            if installer:
                opsys = platform.system()
                if opsys == "Darwin":
                    installer.reset_mac(base, location)
                elif opsys == "Windows":
                    # For windows, we install the tool in a custom directory under ~/.simpleiot/_toolchain/{hash}
                    install_path = Path(base) / key
                    installer.reset_windows(install_path, location)
                elif opsys == "Linux":
                    installer.reset_unix(base, location)
                else:
                    print(f"ERROR: operating system not supported")
            else:
                print(f"ERROR: No toolchain found. Unable to reset toolchain for specified device")
                exit(1)
        except Exception as e:
            print(f"ERROR resetting tool to default settings: {str(e)}")
            exit(1)

    def build(self, base, manufacturer, processor, opsys, version, location, dirpath, command):
        try:
            key = self._make_key(manufacturer, processor, opsys, version)
            installer = self.toolchain_list.get(key, None)
            if installer:
                result = installer.build(base, dirpath, command)
                return result
            else:
                print(f"ERROR: unable to find toolchain for specified device")
                exit(1)
        except Exception as e:
            print(f"ERROR running tool: {str(e)}")
            print(traceback.format_exc())
            exit(1)

    def build_and_flash(self, base, manufacturer, processor, opsys, version, location, dirpath, command):
        try:
            key = self._make_key(manufacturer, processor, opsys, version)
            installer = self.toolchain_list.get(key, None)
            if installer:
                result = installer.build_and_flash(base, dirpath, command)
                return result
            else:
                print(f"ERROR: unable to find toolchain for specified device")
                exit(1)
        except Exception as e:
            print(f"ERROR running tool: {str(e)}")
            print(traceback.format_exc())
            exit(1)

    #
    # This lists the available toolchains this user can install.
    # This returns all the concrete ToolChain classes registered on this system.
    #
    def list_available(self):
        return self.toolchain_list
