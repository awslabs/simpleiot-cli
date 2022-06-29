#!/bin/bash
#
# This only works on a Mac that has homebrew installed.
#

if ! [ -x "$(command -v brew)" ]; then
  echo "ERROR: homebrew needs to be installed first. Please go here: https://brew.sh/"
  exit 1
fi

if ! [ -x "$(command -v arduino-cli)" ]; then
  brew install arduino-cli
fi

if ! [ -x "~/Library/Arduino15/arduino-cli.yaml" ]; then
  arduino-cli config init --overwrite 
fi
arduino-cli config set board_manager.additional_urls https://dl.espressif.com/dl/package_esp32_index.json 
arduino-cli config set library.enable_unsafe_install true
arduino-cli core update-index 
arduino-cli core install esp32:esp32
arduino-cli lib install ArduinoJson
arduino-cli lib install MQTT
arduino-cli lib install FastLED
arduino-cli lib install TinyGPSPlus-ESP32
arduino-cli lib install --git-url https://github.com/m5stack/M5Core2.git
arduino-cli lib install --git-url https://github.com/m5stack/UNIT_ENV.git
arduino-cli lib install --git-url https://github.com/m5stack/UNIT_ENCODER.git
arduino-cli lib install --git-url https://github.com/aws-samples/arduino-aws-greengrass-iot.git

# This will change to external github repo once it's available.
#
arduino-cli lib install --git-url https://gitlab.aws.dev/envision-engineering-amer/industry-accelerators/simpleiot/simpleiot-arduino.git


# Now make sure the serial interface is there.
#
if ! [ -d "venv" ]; then
  echo "Creating python virtual environment"
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
else
  source venv/bin/activate
fi

devices=$(python list_cp210_devices.py)
if [ -z "$devices" ]
then
  echo "ERROR: no serial drivers for the M5Stack installed. Please install Mac CP210x drivers from here: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers"
  exit
fi

echo "Demo build tool installation done!"
echo "Now run:"
echo "   % source env/bin/activate"
echo "   % invoke build {your sketch}"
