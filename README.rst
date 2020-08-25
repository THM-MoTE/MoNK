MoNK - A MOdelica iNKscape extension
====================================

.. image:: https://travis-ci.com/THM-MoTE/MoNK.svg?branch=master
    :target: https://travis-ci.com/THM-MoTE/MoNK

MoNK is a extension for `Inkscape`_ to produce graphical annotation strings for Modelica from an Inkscape SVG image.
Once installed it adds the new export format "Modelica annotation (*.mo)" to the File -> Save as.. menu.

The SVG standard is much more expressive than Modelica annotations.
Not every SVG image can be translated to a Modelica file.
At the same time, Modelica includes high-level concepts such as fill patterns, which cannot be easily parsed from an SVG file.
Therefore, MoNK implements functionality on a best-effort basis, including the features that are most often used in Inkscape and in Modelica.
The goal is to allow drawing icons for Modelica classes in Inkscape that can be used in Modelica with minimal manual effort.

This project supersedes the Modelica vector graphics editor `MoVE`_ in the Modelica Tool Ensemble `MoTE`_.

.. _Inkscape: https://inkscape.org/
.. _MoVE: https://github.com/THM-MoTE/MoVE
.. _MoTE: https://github.com/THM-MoTE

Installation
------------

If Python is installed on your machine, you can just run

``python setup.py install_ink``

from inside the main folder of this project and the script will automatically locate your Inkscape extension folder and place the necessary files in that folder.

Alternatively, you can download a release distribution from GitHub, which only contains the files that need to be put in the Inkscape extension folder.
The correct folder is:

- For Windows: ``%userprofile%\AppData\Roaming\inkscape\extensions``
- For Linux: ``~/.config/inkscape/extensions/``


Features
--------

Supported SVG elements and attributes:

- ``<rect>``
- ``<path>`` (non-smooth)
- ``<circle>``
- ``<ellipse>``
- ``<text>`` and ``<tspan>``
- Inkscape ellipse arcs (``sodipodi:type = "arc"``)
- ``<g>`` (including nested transformations)
- ``transform`` attribute (single transform statement w/o skew and scale)
- ``stroke`` and ``fill`` css attributes (rgb or hex)
- ``stroke-width`` css attribute
- ``marker-start`` and ``marker-end`` (any non-empty marker will result in ``Arrow.Open``)
- css attributes ``horizontalAlignment``, ``font-style``, ``font-weight``, ``text-decoration``, ``font-family``, and ``font-size`` for ``<text>``
- ``viewBox`` attribute


Unsupported SVG elements and attributes:

- Smooth paths (path characters ``C``, ``c``, ``S``, ``s``, ``Q``, ``q``, ``T``, ``t``, ``A``, ``a``)
- css attributes ``stroke-dasharray`` and ``stroke-dashoffset``
- css attributes ``fill-rule`` and ``fill-opacity``
- css ``stroke-width`` values ``inherit`` or percent values
- corner radius for ``<rect>``
- actual parsing of different marker types for ``marker-start`` and ``marker-end``
- complex ``transform`` attributes including skew and scale or multiple statements
- ``<image>``, ``<line>``, ``<polygon>``, ``<polyline>``, and other tags not listed as supported


Supported Modelica elements and attributes:

- ``Line`` (non-smooth)
- ``Polygon`` (non-smooth)
- ``Rectangle``
- ``Ellipse`` (including ``tartAngle`` and ``endAngle``)
- ``Text``
- ``LinePattern.None``, ``LinePattern.Solid``
- ``FillPattern.None``, ``FillPattern.Solid``
- ``lineThickness`` attribute
- ``fillColor`` and ``lineColor`` attributes
- ``Arrow.Open`` and ``Arrow.None``
- all ``TextAlignment``s
- all ``TextStyle``s


Unsupported Modelica elements and attributes:

- ``LinePattern``s ``Dash``, ``Dot``, ``DashDot``, and ``DashDotDot``
- ``FillPattern``s ``Horizontal``, ``Vertical``, ``Cross``, ``Forward``, ``Backward``, ``CrossDiag``, ``HorizontalCylinder``, ``VerticalCylinder``, and ``Sphere``
- ``radius`` and ``borderPattern`` for ``Rectangle``
- ``Smooth.Bezier``
- ``Arrow.Filled``, ``Arrow.Half``
- ``extent`` of ``Text`` annotation is not scaled to actual text size, because this would require rendering the text
- ``Bitmap``

Tips and workarounds for unsupported elements and attributes
------------------------------------------------------------

The following manual adjustments may be necessary for annotations produced by this extension:

* ``lineThickness`` and ``thickness`` attributes are zoom-invariant in OpenModelica, which can require the use of smaller thickness values
* ``Text`` elements might not have the correct size, as this can only be approximated without actually rendering the text
* smooth ``Line`` and ``Polygon`` elements have to be drawn without smooth elements and can then be smoothed afterwards by changing the ``smooth`` parameter in OpenModelica