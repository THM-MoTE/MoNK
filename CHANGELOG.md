# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) 
and this project adheres to [Semantic Versioning](http://semver.org/).

## \[Unreleased\]

### Added

* description of script parameters in readme
* `strict` parameter now does lead to exceptions
* support for corner radius of `<rect>` elements
* support for `"none"` value for color definitions
* experimental support for `transform` values with multiple elements
* support for `transform` values with scale components

### Changed

* better description what it means that `fill-rule` is not supported

### Fixed

[nothing]

## \[0.2.0\]

### Added

* Unit tests in `test/runtests.py`
* Travis CI pipeline testing code on Windows and Linux with Python 2.7 and 3.7
* Readme, changelog and license files

### Removed

* Ruby script (because it was outdated and less convenient than python version)

### Changed

* Moves python code to main directory
* Changed name of the project from svg2modelica to MoNK
* Updates extension for compatibility with Inkscape 1.0
* Makes code conform to pycodestyle
* Setup now contains all dependencies and `python setup.py install` installs these dependencies
* Old install script is now called with `python setup.py install_ink`
* Creates inkscape extension directory if it does not exist

### Fixed

[nothing]

## \[0.1.0\]

### Added

* Full Python script with setup
* Ruby script

### Changed

[nothing]

### Fixed

[nothing]