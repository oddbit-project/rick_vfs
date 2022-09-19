# Welcome to Rick-vfs

[![Tests](https://github.com/oddbit-project/rick_vfs/workflows/Tests/badge.svg?branch=master)](https://github.com/oddbit-project/rick_vfs/actions)
[![pypi](https://img.shields.io/pypi/v/rick_vfs.svg)](https://pypi.org/project/rick_vfs/)
[![license](https://img.shields.io/pypi/l/rick_vfs.svg)](https://github.com/oddbit-project/rick_vfs/blob/master/LICENSE)

Rick-vfs is a high-level abstraction library for file operations on local repositories (a locally accessible folder) and 
Minio/S3 object storage systems. The main goal is to provide a set of common interface functions with analogous behaviour,
to interact with both scenarios.

The intention of "analogous behaviour" is to mimick overall intent and response type, when possible. There will always
be differences between invoking a given method on two different backends.

