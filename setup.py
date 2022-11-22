#!/usr/bin/env python

from sys import platform
from setuptools import setup, find_packages

import os, glob

extra_options={}

if platform == 'darwin':
    extra_options=dict(
        options=dict(
            py2app=dict(
                argv_emulation=True,
                plist='py2app/Info.plist',
                packages=['PIL'],
                resources=['config', 'icons'],
                iconfile='py2app/app.icns',
                includes=['pystray._darwin', 'pynput.keyboard._darwin', 'pynput.mouse._darwin'],
            )
        ),
        app=['main.py'],
    )
elif platform == 'win32':
    import py2exe

    def find_data_files(source,target,patterns):
        """Locates the specified data-files and returns the matches
        in a data_files compatible format.

        source is the root of the source data tree.
            Use '' or '.' for current directory.
        target is the root of the target data tree.
            Use '' or '.' for the distribution directory.
        patterns is a sequence of glob-patterns for the
            files you want to copy.
        """
        if glob.has_magic(source) or glob.has_magic(target):
            raise ValueError("Magic not allowed in src, target")
        ret = {}
        for pattern in patterns:
            pattern = os.path.join(source,pattern)
            for filename in glob.glob(pattern):
                if os.path.isfile(filename):
                    targetpath = os.path.join(target,os.path.relpath(filename,source))
                    path = os.path.dirname(targetpath)
                    ret.setdefault(path,[]).append(filename)
        return sorted(ret.items())

    extra_options=dict(
        windows= [dict(
            script='main.py',
            dest_base='moonlight-desktop',
            icon_resources=[(1, 'py2exe/app.ico')]
        )],
        data_files=find_data_files('', '', ['icons/*.*', 'config/*.*'])
    )

setup(
    name='moonlight-desktop',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'pynput>=1.7.1',
        'pyyaml>=5.3.1',
        'pystray>=0.15.0',
        'pillow==9.3.0',
    ],
    extras_require={
        ':sys_platform=="win32"': ['pywin32', 'py2exe @ https://github.com/albertosottile/py2exe/releases/download/v0.9.3.2/py2exe-0.9.3.2-cp37-none-win32.whl'],
        ':sys_platform=="darwin"': ['pyobjc-framework-Quartz>=6.2', 'py2app>=0.21', 'psutil'],
    },
    **extra_options
)
