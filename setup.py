#!/usr/bin/env python

import os
import re

from pathlib import Path
from codecs import open
from setuptools import find_packages, setup


here = Path(__file__).parent

# Load the package metadata from the __init__.py file as a dictionary.
pkg = {}
with open(here / 'fastapi_rfc7807' / '__init__.py', 'r', 'utf-8') as f:
    pkg = {k: v for k, v in re.findall(r"^(__\w+__) = \'(.+)\'", f.read(), re.M)}

# Load the README
readme = ''
if os.path.exists(here / 'README.md'):
    with open(here / 'README.md', 'r', 'utf-8') as f:
        readme = f.read()


setup(
    name=pkg['__title__'],
    version=pkg['__version__'],
    description=pkg['__description__'],
    license=pkg['__license__'],
    long_description=readme,
    long_description_content_type='text/markdown',
    url=pkg['__url__'],
    author=pkg['__author__'],
    author_email=pkg['__author_email__'],
    packages=find_packages(),
    package_data={
        '': ['LICENSE'],
        'fastapi_rfc7807': ['py.typed'],
    },
    include_package_data=True,
    python_requires='>=3.8',
    install_requires=[
        'fastapi',
        # FIXME: temporarily pinned as the 0.14.x release has breaking changes and fastapi
        #   has not yet been updated for them.
        'starlette==0.13.6',
        'pydantic',
    ],
    keywords=[
        'fastapi', 'errors', 'middleware', 'rfc7807',
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
    ],
    zip_safe=False,
)
