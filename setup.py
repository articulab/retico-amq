"""
Setup script.

Use this script to install the ActiveMQ reader/writer incremental modules for the retico framework.
Usage:
    $ python3 setup.py install
The run the simulation:
    $ retico [-h]
"""

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

import retico_amq

config = {
    "description": "The ActiveMQ reader/writer incremental modules for the retico framework",
    "author": "Marius Le Chapelier",
    "url": "https://github.com/articulab/retico-amq",
    "download_url": "https://github.com/articulab/retico-amq",
    "author_email": "mariuslechapelier@gmail.com",
    "version": retico_amq.__version__,
    "install_requires": ["retico-core~=0.2.0"],
    "packages": find_packages(),
    "name": "retico-amq",
}

setup(**config)
