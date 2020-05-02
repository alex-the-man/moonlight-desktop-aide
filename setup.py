#!/usr/bin/env python

from sys import platform
from setuptools import setup, find_packages

if platform == 'darwin':
    extra_options=dict(
        options=dict(
            py2app=dict(
                argv_emulation=True,
                resources=['config']
            )
        )
    )

setup(
    name='moonlight-desktop',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'pynput>=1.6.8',
        'pyyaml>=5.3.1',
        'pystray>=0.15.0'
    ],
    extras_require={
        ":sys_platform=='win32'": ['pypiwin32', 'py2exe'],
        ":sys_platform=='darwin'": ['pyobjc-framework-Quartz>=6.2', 'py2app>=0.21']
    },
    app=['moonlight-desktop/__main__.py'],
    **extra_options
)