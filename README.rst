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

Alternatively, you can download a `release distribution from GitHub`_, which only contains the files that need to be put in the Inkscape extension folder.
The correct folder is:

- For Windows: ``%userprofile%\AppData\Roaming\inkscape\extensions``
- For Linux: ``~/.config/inkscape/extensions/``

.. _release distribution from GitHub: https://github.com/THM-MoTE/MoNK/releases/latest


Script parameters
-----------------

The main script of MoNK is found in ``src/svg2modelica.py``.
This file is called from within Inkscape to print the resulting Modelica code on stdout.
It can take the following parameters:

- ``svgfile`` is the filename of the SVG document that should be translated.
  This must be the first parameter.
- ``--modelname=SomeString`` (shorthand ``-m SomeString``) determines the model name that should be written to the Modelica output.
  This should be the same name as the file name chosen in Inkscape in order to load the model in an IDE like OpenModelica to examine the results.
- ``--strict=True|False`` (shorthand ``-s True|False``) if true, non-translatable elements in the SVG document are treated as errors.
  Otherwise they are simply ignored.
- ``--normalize_extent=True|False`` (shorthand ``-n True|False``) if true, the ``extent`` attribute of the ``coordinateSystem`` element in the Modelica output will be normalized to fit within ``{{-100, -100}, {100, 100}}``.
  This is not required by the Modelica specification, but a de facto standard that is also assumed in OMEdit.
  Unnormalized icons may look fine in the diagram view, but might be cropped in the tree view for selecting classes.


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
- css attribute ``fill-opacity`` and ``stroke-opacity``
- css ``stroke-width`` values given as ``inherit`` or percentages
- actual parsing of different marker types for ``marker-start`` and ``marker-end``
- ``transform`` attributes including skew and scale expressions (directly or in matrix form)
- ``<image>``, ``<line>``, ``<polygon>``, ``<polyline>``, and other tags not listed as supported
- ``<path>`` with "holes" (settings for css property ``fill-rule`` are ignored)


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
- ``borderPattern`` for ``Rectangle``
- ``Smooth.Bezier``
- ``Arrow.Filled``, ``Arrow.Half``
- ``extent`` of ``Text`` annotation is not scaled to actual text size, but only approximated (exact scaling would require rendering the text)
- ``Bitmap``

Tips and workarounds for unsupported elements and attributes
------------------------------------------------------------

The following manual adjustments may be necessary for annotations produced by this extension:

- ``lineThickness`` and ``thickness`` attributes are zoom-invariant in OpenModelica, which can require the use of smaller thickness values
- ``Text`` elements might not have the correct size, as this can only be approximated without actually rendering the text
- smooth ``Line`` and ``Polygon`` elements have to be drawn without smooth elements and can then be smoothed afterwards by changing the ``smooth`` parameter in OpenModelica
- Always use "Save a Copy..." instead of "Save as..." in Inkscape, since ``.mo`` is only an export format that cannot be imported again.
  If you want to change your drawing afterwards, you will still have to save a ``.svg`` version of it.