#!/usr/bin/env python

# © 2022 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#
# SimpleIOT project.
# Author: Ramin Firoozye (framin@amazon.com)
#

from setuptools import setup, find_packages
from pathlib import Path
import sys
import semver
import configparser
import os
import traceback

#
# This function automatically bumps up the current [version] section in setup.cfg file.
# By default it bumps up the last/patch version of the semantic version value (i.e. #.#.#)
# It then writes the value back out so each time you run pypideploy, the version is
# automatically pushed up.
#
# We've added a [version] section to the standard setup.cfg file. Two key/values there are:
# [version]
# pypi_test_version=1.0.1
# pypi_version=1.0.1
#
# Since this is usually loaded by the pypideploy script, it can set an environment variable
# indicating whether it's a test release or a production one. If not set, it will go out to
# the test one.
#
# That environment variable will indicate which version we will be bumping up.
#
def bump_and_return_version():
    initial_value = "1.0.0"
    bump_type = None
    result = None
    try:
        config = configparser.ConfigParser()
        config.read('setup.cfg')
        version_section = config["version"]
        if not version_section:
            config['version']['pypi_test_version'] = initial_value
            config['version']['pypi_version'] = initial_value
            result = initial_value
        else:
            is_full = os.environ.get("IOT_DEPLOY_PYPI", 0)
            if is_full == 1:
                bump_type = "PyPi"
                pypi_version_str = version_section.get('pypi_version')
                if pypi_version_str:
                    pypi_version = semver.VersionInfo.parse(pypi_version_str)
                    pypi_version = pypi_version.bump_patch()
                    version_section['pypi_version'] = str(pypi_version)
                    result = str(pypi_version)
            else:
                bump_type = "PyPi Test"
                pypi_test_version_str = version_section.get('pypi_test_version')
                if pypi_test_version_str:
                    pypi_test_version = semver.VersionInfo.parse(pypi_test_version_str)
                    pypi_test_version = pypi_test_version.bump_patch()
                    version_section['pypi_test_version'] = str(pypi_test_version)
                    result = str(pypi_test_version)

        with open('setup.cfg', 'w') as config_file:
            config.write(config_file)

        print(f"Bumping {bump_type} version to {result}")
        return result

    except Exception as e:
        print(f"ERROR processing setup.cfg file: {str(e)}")
        print(traceback.format_exc())
        exit(1)


with open(Path('requirements.txt')) as f:
    required = f.read().splitlines()

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(name='simpleiot-cli',
      version=bump_and_return_version(),
      description='SimpleIOT command line interface',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='http://github.com/awslabs/simpleiot-cli',
      author='Ramin Firoozye',
      author_email='framin@amazon.com',
      license='Apache 2.0',
      py_modules=['iot'],
      packages=find_packages() + ["simpleiot/demo", "simpleiot/demo/m5gif"],
      package_data={'simpleiot/demo': ['*'],
                    'simpleiot/demo/m5gif': ['*']
                    },
      install_requires=required,
      download_url="https://github.com/awslabs/simpleiot-cli",
      keywords=["simpleiot", "simpleiot-cli", "iot", "aws", "awslabs", "cli"],
      classifiers=[
          "Environment :: Console",
          "Intended Audience :: Developers",
          "Intended Audience :: System Administrators",
          "Operating System :: Microsoft :: Windows",
          "Operating System :: MacOS :: MacOS X",
          "License :: OSI Approved :: Apache Software License",
          "Topic :: Software Development",
          "Topic :: Software Development :: Embedded Systems",
          "Topic :: System :: Hardware",
          "Topic :: System :: Installation/Setup",
          "Topic :: Utilities"
      ],
      entry_points={
          'console_scripts': [
              'iot=simpleiot.iot:iotcli'
          ],
      },
      )
