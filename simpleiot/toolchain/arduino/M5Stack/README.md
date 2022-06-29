# Install M5Stack Toolchain for Mac

---
NOTE:

This method of installing the toolchain has been deprecated. It is left here in case the
code can be reused for testing access to the USB port.

The toolchain install has been integrated into the 'iot toolchain install' command, which
uses the mechanisms installed under the 'buildtool' directory.

----

This script installs the toolchain for building Arduino firmware for M5Stack (ESP32) devices. 

*Please read to the end for more information on installing the USB-to-serial drivers.*

If you install this, you will be able to use the SimpleIOT CLI to build/flash firmware to the M5 device in one go.

Although the M5Stack device is not required to develop IOT products, it's a fairly inexpensive ESP-32 based device and the demos and basic firmware are designed to run on it. If you want to play along with the demos, we recommend you get one. 

The [M5Go IOT Starter Kit](https://shop.m5stack.com/products/m5go-iot-starter-kit-stem-education) comes with a basic device and several input sensors which makes it easy to test sending data to the cloud in your own stack.


### The Development Toolchain

To develop firmware for devices, it's often necessary to download, install, and configure a fairly complex toolchain. This script tries to automate that process so you can be up and running fairly quickly.


#### NOTE: The script currently only supports installation on a Mac. A Windows version is in the works.

Installation of this tool is not necessary, but will enable use of the `iot firmware flash` command so you can go quickly from the firmware generated via `iot firmware generate` to directly flashing an M5 demo device in two commands.

The script assumes that you have [Homebrew](https://brew.sh/) installed. If not, please install that first from the link.

If you already have [arduino-cli](https://arduino.github.io/arduino-cli/0.19/installation/) command-line tool installed, please edit the install script and comment out the `brew install arduino-cli` command.
 
**NOTE**: Please install the CP210x drivers and plug in your M5 device *before* starting 
the installation process. The installer checks to make sure the scripts find a compatible
M5 device port.

To run make sure you're in the installer directory (the one with this README file) not the
CLI directory. Plug in your M5Stack device with a USB cable. Then run:


```
% ./install-arduino-cli.sh
```

This assumes the virtual env was set up at the top simpleiot-cli directory path.

Once done, you should be able to test the version in the terminal:

```
% arduino-cli version
arduino-cli alpha Version: 0.19.3 Commit: 12f1afc2 Date: 2021-10-11T15:14:04Z
```

### Behind the Scenes

The script installs `arduino-cli` using Homebrew. It then configures it with the necessary libraries (both remote and local) so it can be invoked via the command line.

If you prefer building and flashing using an IDE, there are a number of options including the [Arduino IDE](https://www.arduino.cc/en/software), [Visual Studio Code](https://code.visualstudio.com/) with the [Arduino Extension](https://marketplace.visualstudio.com/items?itemName=vsciot-vscode.vscode-arduino), or the [PlatformIO IDE for VSCode](https://platformio.org/install/ide?install=vscode).

The Arduino Command-Line-Interface allows you to perform all the builds from the command line and then flash the code onto the device using a USB cable.

The SimpleIOT command-line-interface (CLI) wraps around it and has two commands where it can generate sample code targeting the M5Stack and then build and flash the code by invoking the *arduino-cli* command:

```
% iot firmware generate --name="hello-world-m5" --project=HelloProject --serial=HW5-0001 --manufacturer=espressif --processor=esp32 --os=arduino --version="1.0.0"
% iot firmware flash --zip=simpleiot_demo_arduino_esp32.zip
```

This auto-generates the *Hello World* firmware, pre-loads it with the certificates and necessary credentials. You can unzip the downloaded archive and manually build and flash the firmware. 

If the *arduino-cli* tool is installed, the `iot firmware flash` command will unzip the archive in to a temporary directory, build the code, and upload it to the device in one go. The command checks to make sure the *arduino-cli* command is installed and if a USB device with ids associated with M5 devices are plugged in.

The installer script also installs both Greengrass SDK for Arduino as well as the SimpleIOT SDK for Arduino into the arduino-cli library.

If you already have `arduino-cli` installed and configured, please DO NOT use this installation script. Instead, look inside and manually merge the commands necessary to configure arduino-cli, otherwise you may lose your previous settings.


### USB Port

To be able to upload firmware to the M5 device via USB, you will also need to install the CP210 USB-to-serial drivers.

This can be found at the [SiLabs download site](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers). Click on the *Downloads* tab and download the [CP210x VCP Mac OSX Driver](https://www.silabs.com/documents/public/software/Mac_OSX_VCP_Driver.zip) zip file.

Double-click to unzip and it extracts a file called `SiLabsUSBDriverDisk.dmg`. This is the installer DMG file. Double-click this to run it and it runs the driver installation script.

It may require you to reboot. If so, please do so. 

Once installed, you should be able to plug the target M5 device into USB port using a USB cable and have the Simpleiot CLI discover the port for output.
