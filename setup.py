# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division,
                        print_function)
from builtins import *

import sys
import os
import glob
import shutil
import tarfile
import zipfile
from setuptools import setup, Command
from setuptools.command.install import install
import io

data_files = [
    (os.path.relpath(os.path.dirname(x), "res"), [x])
    for x in glob.glob("res/**")
]


def determine_dir(name, filename, defaults={}):
    if not os.path.exists(".paths"):
        os.mkdir(".paths")
    filepath = os.path.join(".paths", filename)
    if os.path.exists(filepath):
        with io.open(filepath, 'r', encoding="UTF-8") as f:
            return f.read()
    default = defaults.get(sys.platform, "")
    msg = "Please specify the {} or press enter to use the default.\n[{}]"
    dirname = input(msg.format(name, default))
    if len(dirname) == 0:
        dirname = default
    msg = "Your path configuration will be saved in the file {} " \
        + "for further use."
    print(msg.format(filepath))
    with io.open(filepath, 'w', encoding="UTF-8") as f:
        f.write(dirname)
    return dirname


def determine_ext():
    return determine_dir("inkscape extension directory", "ext.txt", defaults={
        "win32": r'C:\Program Files\Inkscape\share\extensions',
        "cygwin": r'C:\Program Files\Inkscape\share\extensions',
        "linux": r'/usr/share/inkscape/extensions/',
    })


def determine_user_ext():
    return determine_dir(
        "inkscape user extension directory", "user_ext.txt", defaults={
            "win32": os.path.expanduser(
                r'~\AppData\Roaming\inkscape\extensions'
            ),
            "cygwin": os.path.expanduser(
                r'~\AppData\Roaming\inkscape\extensions'
            ),
            "linux": os.path.expanduser(
                r'~/.config/inkscape/extensions/'
            ),
        }
    )


class BdistInkscape(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        outfile = "{}-{}".format(
            self.distribution.metadata.get_name(),
            self.distribution.metadata.get_version()
        )
        files = []
        files.extend([
            (f, os.path.relpath(f, "src"))
            for f in glob.glob("src/**")
            if ".egg-info" not in f
        ])
        files.extend([
            (f, os.path.relpath(f, "res"))
            for f in glob.glob("res/**")
        ])
        with tarfile.open("dist/{}.tar.gz".format(outfile), "w:gz") as tf:
            for f, aname in files:
                tf.add(f, arcname=aname)
        with zipfile.ZipFile("dist/{}.zip".format(outfile), "w") as zf:
            for f, aname in files:
                zf.write(f, arcname=aname)


class InstallToExtensionDir(install):
    def run(self):
        # copy source files to extension dir
        for f in [x for x in glob.glob("src/**") if ".egg-info" not in x]:
            src = f
            dst = os.path.join(determine_user_ext(), os.path.relpath(f, "src"))
            print("copying %s -> %s" % (src, dst))
            shutil.copyfile(src, dst)
        # copy .inx file(s) to extension dir
        for f in glob.glob("res/**"):
            src = f
            dst = os.path.join(determine_user_ext(), os.path.relpath(f, "res"))
            print("copying %s -> %s" % (src, dst))
            shutil.copyfile(src, dst)


with io.open("README.rst", "r", encoding="utf-8") as f:
    readme = f.read()

version = '0.2.0'
setup(
    name='svg2modelica',
    package_dir={'': 'src'},
    py_modules=['svg2modelica'],
    version=version,
    platforms="any",
    license="MIT",
    description='Inkscape plugin to save document as Modelica annotation.',
    long_description=readme,
    author='Christopher Schölzel',
    author_email='christopher.schoelzel@gmx.net',
    url='https://github.com/CSchoel/svg2modelica',
    download_url='https://github.com/CSchoel/svg2modelica/tarball/' + version,
    keywords=[
        'Modelica', 'inkscape', 'inkscape extension', 'Modelica annotation'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6'
    ],
    install_requires=[
        'future',
        'setuptools'
    ],
    cmdclass={
        'install': InstallToExtensionDir,
        'bdist_ink': BdistInkscape
    },
    data_files=data_files,
    include_package_data=True
)
