#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

version = __import__('rick_vfs').get_version()

# read the contents of README.md
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    description = f.read()

setup(
    name='rick_vfs',
    version=version,
    author="Joao Pinheiro",
    author_email="",
    url="https://git.oddbit.org/OddBit/rick_vfs",
    description='Minio/S3 client VFS abstraction library',
    license='BSD',
    long_description=description,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    long_description_content_type='text/markdown',
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    extras_require={},
    install_requires=[
        'python-magic==0.4.27',
        'minio>=7.1.15',
    ],
    zip_safe=False,
    tests_require=[
    ],
)
