# -*- coding: utf-8 -*-

import getopt
import sys
import lxml.etree as etree
import re
import numpy as np

inkex_available = True

try:
    import inkex
except ImportError:
    inkex_available = False


def identity(x):
    return x


def nonzero(x):
    return abs(x) > 1e-10


class MoNKError(Exception):
    def __init__(self, msg):
        self.msg = msg


INDENT = "    "

re_to_f = re.compile(r"(\-?\d+(?:\.\d+)?(?:e\-?\d+)?)[^\d]*")


def to_f(s):
    return float(re.match(re_to_f, s).group(1))


def to_s(*args, **kwargs):
    decimal_place = kwargs.get("decimal_place", 2)
    res = []
    for f in args:
        s = ("%."+str(decimal_place)+"f") % f
        if (s[-decimal_place:] == "0"*decimal_place):
            s = s[:-decimal_place-1]
        res.append(s)
    if len(res) == 1:
        return res[0]
    return tuple(res)


def tn(el):
    return etree.QName(el.tag).localname


def parse_svg(
        fname, modelname, strict=False, normalize_extent=False,
        text_extent="normal"
):
    with open(fname, "rb") as f:
        parser = etree.XMLParser(encoding="utf-8", ns_clean=True)
        document = etree.parse(f, parser=parser)
    res = "model {1}\n" \
        + "{0}annotation(\n" \
        + "{0}{0}{2}\n" \
        + "{0});\n" \
        + "end {1};"
    main_icon = ModelicaIcon(
        document, normalize_extent=normalize_extent, strict=strict,
        text_extent=text_extent
    )
    print(res.format(INDENT, modelname, main_icon))


def get_style_attribute(el, name):
    if el.get("style") is None:
        return None
    for att in el.get("style").split(";"):
        if att.startswith(name+":"):
            return att[len(name)+1:]
    return None


def get_ns_attribute(el, ns, att):
    return el.get("{%s}%s" % (el.nsmap.get(ns), att))


def transform_units(value, from_unit, to_unit):
    # modelica coordinates are assumed to be mm, so we set 1px = 1mm
    to_mm_factors = {
        "pt": 25.4/72, "px": 1.0, "pc": 304.0/72, "mm": 1.0,
        "cm": 10.0, "in": 25.4
    }
    return value * to_mm_factors[from_unit] / to_mm_factors[to_unit]


class ModelicaElement(object):
    def __init__(self, name, el, n_indent=3, coords=None, strict=False):
        self.name = name
        self.data = {}
        self.elems = []
        self.n_indent = n_indent
        self.strict = strict
        self.add_attributes(el)

    def add_attribute(self, key, value):
        self.data[key] = value

    def add_element(self, modelica_el):
        self.elems.append(modelica_el)

    def add_attributes(self, el):
        pass

    def __str__(self):
        line_delim = "\n"+INDENT*self.n_indent
        inner = line_delim
        if len(self.elems) > 0:
            inner += (","+line_delim).join([str(x) for x in self.elems])
            if len(self.data) > 0:
                inner += ","
            inner += line_delim
        attribs = sorted(self.data.items(), key=lambda x: x[0])
        inner += (","+line_delim).join([
                "{0}= {1}".format(k, v) for k, v in attribs
        ])
        inner += "\n"+INDENT*(self.n_indent-1)
        res = "{0}({1})".format(self.name, inner)
        return res

    def check_unsupported_css(self, el, key, default):
        if not self.strict:
            return  # skip check
        val = get_style_attribute(el, key)
        if val is None:
            return
        if isinstance(default, (int, float)):
            isdefault = np.isclose(float(val), default)
        else:
            isdefault = val == default
        if not isdefault:
            raise MoNKError("css attribute {} is not supported".format(key))


class ModelicaIcon(ModelicaElement):
    def __init__(
            self, doc, n_indent=3, normalize_extent=False, coords=None,
            strict=False, text_extent="normal"
    ):
        # needs to be initialized first, because add_attribute is called in
        # superclass constructor
        self.norm_extent = normalize_extent
        ModelicaElement.__init__(
            self, "Icon", doc, n_indent, coords=coords, strict=strict
        )

    def add_attributes(self, doc):
        coords = ModelicaCoordinateSystem(
            doc.getroot(), n_indent=self.n_indent+1,
            normalize_extent=self.norm_extent
        )
        self.add_element(coords)
        self.add_attribute(
            "graphics",
            ModelicaGraphicsContainer(
                doc, n_indent=self.n_indent+1, coords=coords,
                strict=self.strict, text_extent=text_extent
            )
        )


class ModelicaCoordinateSystem(ModelicaElement):
    def __init__(self, svg, n_indent=4, normalize_extent=False, strict=False):
        # needs to be set first to be available in add_attributes
        self.norm_extent = normalize_extent
        ModelicaElement.__init__(
            self, "coordinateSystem", svg, n_indent=n_indent, strict=strict
        )
        self.px2mm_factor_x = 1
        self.px2mm_factor_y = 1

    def normalize_x(self, x):
        if self.norm_extent:
            return (x - self.x_center) * self.scale
        else:
            return x

    def normalize_y(self, y):
        if self.norm_extent:
            return (y - self.y_center) * self.scale
        else:
            return y

    def normalize_delta(self, delta):
        if self.norm_extent:
            return delta * self.scale
        else:
            return delta

    def add_attributes(self, svg):
        self.add_attribute("preserveAspectRatio", "false")
        self.autoset_extent(svg)

    def set_extent(self, x1, y1, x2, y2):
        w = x2 - x1
        h = y2 - y1
        self.scale = min(200.0/w, 200.0/h)
        self.x_center = (x1 + x2) / 2.0
        self.y_center = (y1 + y2) / 2.0
        if self.norm_extent:
            x1 = -w / 2.0 * self.scale
            x2 = +w / 2.0 * self.scale
            y1 = -h / 2.0 * self.scale
            y2 = +h / 2.0 * self.scale
        self.add_attribute(
            "extent", "{{%s,%s},{%s,%s}}" % to_s(x1, y1, x2, y2)
        )

    def find_extent(self, svg):
        w = to_f(svg.get("width"))
        h = to_f(svg.get("height"))
        if "viewBox" in svg.attrib:
            ws = re.compile(r"\s+")
            xv, yv, wv, hv = [to_f(s) for s in ws.split(svg.get("viewBox"))]
            self.px2mm_factor_x = w / wv
            self.px2mm_factor_y = h / hv
            return [xv, yv-hv, xv+wv, yv]
        else:
            return [0, -h, w, 0]

    def autoset_extent(self, svg):
        ext = self.find_extent(svg)
        self.set_extent(*ext)


class ModelicaGraphicsContainer(object):
    def __init__(
            self, doc, n_indent=4, coords=None, strict=False,
            text_extent="normal"
    ):
        self.n_indent = n_indent
        self.elems = []
        self.coords = coords
        self.strict = strict
        self.text_extent = text_extent
        self.add_descendants(doc.getroot())

    def to_modelica(self, el):
        tag = tn(el)
        if not isinstance(el, etree._Element):
            return None
        if tag in ["defs", "metadata", "namedview"]:
            return None
        elif tag == "rect":
            return ModelicaRectangle(
                el, self.n_indent+1, coords=self.coords, strict=self.strict
            )
        elif tag == "path":
            fill = get_style_attribute(el, "fill")
            if get_ns_attribute(el, "sodipodi", "type") == "arc":
                return ModelicaEllipse(
                    el, self.n_indent+1, coords=self.coords, strict=self.strict
                )
            elif re.match(r".*[zZ]\s*$", el.get("d")):
                return ModelicaPolygon(
                    el, self.n_indent+1, coords=self.coords, strict=self.strict
                )
            elif fill is not None and (fill != "none"):
                return ModelicaPolygon(
                    el, self.n_indent+1, coords=self.coords, strict=self.strict
                )
            else:
                return ModelicaLine(
                    el, self.n_indent+1, coords=self.coords, strict=self.strict
                )
        elif tag == "circle":
            return ModelicaEllipse(
                el, self.n_indent+1, coords=self.coords, strict=self.strict
            )
        elif tag == "ellipse":
            return ModelicaEllipse(
                el, self.n_indent+1, coords=self.coords, strict=self.strict
            )
        elif tag == "text":
            return ModelicaText(
                el, self.n_indent+1, coords=self.coords, strict=self.strict,
                extent=self.text_extent
            )
        else:
            if self.strict:
                raise MoNKError("tag {} is not supported".format(tag))
            return None
        # TODO (nice to have) support bitmap images

    def add_descendants(self, el):
        for c in el.iterchildren():
            if tn(c) == "g":
                self.add_descendants(c)
            else:
                m = self.to_modelica(c)
                if m is not None:
                    self.elems.append(m)

    def add_element(self, modelica_el):
        self.elems.append(modelica_el)

    def __str__(self):
        inner = "\n"+INDENT*self.n_indent
        inner += (",\n"+INDENT*self.n_indent).join(
            [str(x) for x in self.elems]
        )
        inner += "\n"+INDENT*(self.n_indent-1)
        return "{" + inner + "}"


class LinePattern:
    NONE = "LinePattern.None"
    SOLID = "LinePattern.Solid"
    DASH = "LinePattern.Dash"
    DOT = "LinePattern.Dot"
    DASH_DOT = "LinePattern.DashDot"
    DASH_DOT_DOT = "LinePattern.DashDotDot"


class FillPattern:
    NONE = "FillPattern.None"
    SOLID = "FillPattern.Solid"
    HORIZONTAL = "FillPattern.Horizontal"
    VERTICAL = "FillPattern.Vertical"
    CROSS = "FillPattern.Cross"
    FORWARD = "FillPattern.Forward"
    BACKWARD = "FillPattern.Backward"
    CROSS_DIAG = "FillPattern.CrossDiag"
    HORIZONTAL_CYLINDER = "FillPattern.HorizontalCylinder"
    VERTICAL_CYLINDER = "FillPattern.VerticalCylinder"
    SPHERE = "FillPattern.Sphere"


class BorderPattern:
    NONE = "BorderPattern.None"
    RAISED = "BorderPattern.Raised"
    SUNKEN = "BorderPattern.Sunken"
    ENGRAVED = "BorderPattern.Engraved"


class Smooth:
    NONE = "Smooth.None"
    BEZIER = "Smooth.Bezier"


class GraphicItem(object):
    def __init__(self, coords):
        self.coords = coords
        self.offset_x = None
        self.offset_y = None

    def x_coord(self, x):
        res = self.scale_x(x)
        if self.coords is not None:
            res = self.coords.normalize_x(res)
        res += self.offset_x
        return res

    def y_coord(self, y):
        res = self.scale_y(-y)
        if self.coords is not None:
            res = self.coords.normalize_y(res)
        res += self.offset_y
        return res

    def set_origin(self, x, y):
        if self.coords is not None:
            x = self.coords.normalize_x(x)
            y = self.coords.normalize_y(y)
            # remove translational part that comes just from different origin
            self.offset_x = -self.coords.normalize_x(0)
            self.offset_y = -self.coords.normalize_y(0)
        else:
            # every translation should be applied to all points
            self.offset_x = 0
            self.offset_y = 0
        self.add_attribute("origin", "{%s,%s}" % to_s(x, y))

    def set_rotation(self, deg):
        self.add_attribute("rotation", to_s(deg))

    def get_matrix(self, el):
        # get the transformation matrix for this element
        if el is None:
            return np.eye(3, dtype="float32")
        mpar = self.get_matrix(el.getparent())
        mel = self.parse_transform(el.get("transform"))
        return np.dot(mpar, mel)

    def parse_transform(self, transform):
        if transform is None:
            return np.eye(3, dtype="float32")
        # handle multiple transform statements in one string
        parts = re.findall(r"[a-zA-Z]+\s*\([-\d.,\s]+\)", transform)
        if len(parts) > 1:
            mat = np.eye(3, dtype="float32")
            # parse and apply individual transforms right to left
            for p in reversed(parts):
                mat = np.dot(mat, parse_fransform(p))
            return mat
        exp_matrix = re.compile(r"""
            \s*matrix\s*
            \(
                \s*(-?\d+\.?\d*)[\s,]+
                \s*(-?\d+\.?\d*)[\s,]+
                \s*(-?\d+\.?\d*)[\s,]+
                \s*(-?\d+\.?\d*)[\s,]+
                \s*(-?\d+\.?\d*)[\s,]+
                \s*(-?\d+\.?\d*)\s*
            \)\s*
        """, re.VERBOSE)
        exp_translate = re.compile(r"""
            \s*translate\s*
            \(
                \s*(-?\d+\.?\d*)[\s,]+
                \s*(-?\d+\.?\d*)\s*
            \)
        """, re.VERBOSE)
        exp_rotate = re.compile(r"""
            \s*rotate\s*
            \(
                \s*(-?\d+\.?\d*)\s*
                (?:[\s,]+
                    \s*(-?\d+\.?\d*)[\s,]+
                    \s*(-?\d+\.?\d*)\s*
                )?
            \)
        """, re.VERBOSE)
        m_mat = exp_matrix.match(transform)
        m_trans = exp_translate.match(transform)
        m_rot = exp_rotate.match(transform)
        if m_mat is not None:
            g = [float(x) for x in m_mat.groups()]
            mat = np.array([
                [g[0], g[2], g[4]],
                [g[1], g[3], g[5]],
                [0, 0, 1]
            ])
        elif m_trans is not None:
            g = [float(x) for x in m_trans.groups()]
            mat = np.array([
                [1, 0, g[0]],
                [0, 1, g[1]],
                [0, 0, 1]
            ])
        elif m_rot is not None:
            g = [float(x) if x is not None else x for x in m_rot.groups()]
            if g[1] is not None:
                t = self.parse_transform(
                    "translate({1}, {2})".format(g[1], g[2])
                )
                r = self.parse_transform("rotate({1})".format(g[0]))
                ti = self.parse_transform(
                    "translate({1}, {2})".format(-g[1], -g[2])
                )
                mat = np.dot(np.dot(t, r), ti)
            else:
                alpha = float(g[0]) / 180.0 * np.pi
                mat = np.array([
                    [np.cos(alpha), -np.sin(alpha), 0],
                    [np.sin(alpha), np.cos(alpha), 0],
                    [0, 0, 1]
                ])
        else:
            # NOT SUPPORTED: does not handle skew and scale
            if self.strict:
                raise MoNKError("cannot handle transform={}".format(transform))
            # ignore what we cannot handle
            mat = np.eye(3, dtype="float32")

        flip = np.array([[1, 0, 0], [0, -1, 0], [0, 0, 1]], dtype="float32")
        # flip coordinates, apply matrix to flipped points and flip back again
        # this is required because the y axis of the SVG coordinate system
        # starts at the top but the y axis of modelica starts at the bottom of
        # the icon
        return np.dot(np.dot(flip, mat), flip)

    def decompose_matrix(self, mat):
        # decompose transformation matrix to angle + origin form
        # we assume that the matrix has the following form
        # sx * cos(alpha)   -sy * sin(alpha)   tx
        # sx * sin(alpha)    sy * cos(alpha)   ty
        #      0                   0            1
        # 1. Get translation
        tx = mat[0, 2]
        ty = mat[1, 2]
        # 2. Get scaling (since sin²(x) + cos²(x) = 1)
        sx = np.sqrt(mat[0, 0] ** 2 + mat[1, 0] ** 2)
        sy = np.sqrt(mat[0, 1] ** 2 + mat[1, 1] ** 2)
        # sign for scaling is ambiguous due to symmetries in trigonometric
        # functions (sin(-x) = -sin(x) and cos(-x) = cos(x))
        # therefore we only look for the sign of the diagonal and arbitrarily
        # flip one of the axes if required
        if not nonzero(mat[1, 0]):
            flipped = np.sign(mat[0, 0]) != np.sign(mat[1, 1])
        else:
            flipped = np.sign(mat[1, 0]) == np.sign(mat[0, 1])
        if flipped:
            sx *= -1
        # 3. Remove scaling and obtain rotational angle
        alpha = np.arctan2(mat[1, 0] / sx, mat[0, 0] / sx)
        if self.strict:
            # check that decomposed matrix equals the original matrix
            ref = np.array(
                [
                    [sx * np.cos(alpha), sy * -np.sin(alpha), tx],
                    [sx * np.sin(alpha), sy * np.cos(alpha), ty],
                    [0, 0, 1]
                ],
                dtype="float32"
            )
            if not np.all(np.isclose(
                    mat.flatten(), ref.flatten(), rtol=1e-4, atol=1e-3
            )):
                raise MoNKError("".join([
                    "Transformation matrix is not reducible to angle + ",
                    "origin [+ scaling] form.\n\n",
                    "{0}\n!=\n{1}"
                ]).format(mat, ref))
        return tx, ty, sx, sy, alpha

    def autoset_rotation_and_origin(self, el):
        mat = self.get_matrix(el)
        tx, ty, sx, sy, alpha = self.decompose_matrix(mat)
        self.set_origin(tx, ty)
        if nonzero(alpha):
            self.set_rotation(alpha/np.pi*180)
        self.tx = tx
        self.ty = ty
        self.sx = sx
        self.sy = sy

    def scale_x(self, x):
        return self.scale(x, self.sx)

    def scale_y(self, y):
        return self.scale(y, self.sy)

    def scale_thickness(self, x):
        return self.scale(x, np.mean([abs(self.sx), abs(self.sy)]))

    def scale(self, val, s):
        return val * s


class FilledShape(object):
    def set_line_color(self, r, g, b):
        self.add_attribute(
            "lineColor", "{%d,%d,%d}" % (round(r), round(g), round(b))
        )

    def autoset_line_color(self, el):
        lc = self.find_line_color(el)
        if lc is not None and lc != "{0,0,0}" and self.has_stroke():
            self.add_attribute("lineColor", lc)

    def find_line_color(self, el):
        att = get_style_attribute(el, "stroke")
        return self.attribute_value_to_color(att)

    def attribute_value_to_color(self, att):
        if att is None or att == "none":
            return None
        if att.startswith("#"):
            return self.css_hex_to_modelica(att)
        if att.startswith("rgb"):
            return self.css_rgb_to_modelica(att)
        if self.strict:
            # NOT SUPPORTED: currentColor, inherit, url(),
            # css color names
            raise MoNKError("color definition {} is not supported".format(att))
        return None

    def set_fill_color(self, r, g, b):
        self.add_attribute(
            "fillColor", "{%d,%d,%d}" % (round(r), round(g), round(b))
        )

    def find_fill_color(self, el):
        att = get_style_attribute(el, "fill")
        return self.attribute_value_to_color(att)

    def autoset_fill_color(self, el):
        fc = self.find_fill_color(el)
        if fc is not None and fc != "{0,0,0}" and self.has_fill():
            self.add_attribute("fillColor", fc)

    def set_line_pattern(self, lp):
        self.add_attribute("pattern", lp)

    def find_line_pattern(self, el):
        att = get_style_attribute(el, "stroke")
        if att == "none":
            return LinePattern.NONE
        # NOT SUPPORTED: Dash, Dot, DashDot, DashDotDot,
        # NOT SUPPORTED: css stroke-dasharray and stroke-dashoffset values
        self.check_unsupported_css(el, "stroke-dasharray", "none")
        self.check_unsupported_css(el, "stroke-dashoffset", 0)
        self.check_unsupported_css(el, "stroke-opacity", 1)
        return LinePattern.SOLID

    def autoset_line_pattern(self, el):
        lp = self.find_line_pattern(el)
        if lp != LinePattern.SOLID:
            self.add_attribute("pattern", lp)

    def set_fill_pattern(self, lp):
        self.add_attribute("fillPattern", lp)

    def has_fill(self):
        return "fillPattern" in self.data \
            and self.data["fillPattern"] != FillPattern.NONE

    def has_stroke(self):
        return "pattern" not in self.data \
            or self.data["pattern"] != LinePattern.NONE

    def find_fill_pattern(self, el):
        att = get_style_attribute(el, "fill")
        if att == "none":
            return FillPattern.NONE
        # NOT SUPPORTED (modelica): Horizontal Vertical Cross Forward
        # Backward CrossDiag HorizontalCylinder VerticalCylinder Sphere
        # NOT SUPPORTED (svg): css fill-rule (ignored, because not relevant)
        # NOT SUPPORTED (svg): css fill-opacity
        self.check_unsupported_css(el, "fill-opacity", 1)
        return FillPattern.SOLID

    def autoset_fill_pattern(self, el):
        fp = self.find_fill_pattern(el)
        if fp != FillPattern.NONE:
            self.add_attribute("fillPattern", fp)

    def set_line_thickness(self, x):
        if self.coords is not None:
            x = self.coords.normalize_delta(x)
            x = self.scale_thickness(x)
        self.add_attribute("lineThickness", to_s(x))

    def find_line_thickness(self, el):
        att = get_style_attribute(el, "stroke-width")
        if att is None:
            return None
        if "%" in att or att == "inherit":
            # NOT SUPPORTED (svg): inherit, percentage
            # (need viewport info for that)
            if self.strict:
                raise MoNKError("stroke-width {} not supported".format(att))
            return 1.0
        return to_f(att)

    def autoset_line_thickness(self, el):
        val = self.find_line_thickness(el)
        if val is not None and self.has_stroke():
            self.set_line_thickness(val)

    def css_hex_to_modelica(self, hexstr):
        hexstr = hexstr[1:]
        sz = 2 if len(hexstr) > 3 else 1
        return "{%d,%d,%d}" % tuple(
            [int(hexstr[i*sz:i*sz+sz], 16) for i in range(3)]
        )

    def css_rgb_to_modelica(self, rgbstr):
        match = re.match(
            r"\s*rgb\s*\(\s*(\d+\%?)\s*,\s*(\d+\%?)\s*,\s*(\d+\%?)\s*\)\s*",
            rgbstr
        )
        rgb = match.groups()
        if "%" in rgb[0]:
            rgb = [round(int(x[0:-2])*255.0/100) for x in rgb]
        else:
            rgb = [int(x) for x in rgb]
        return "{%d,%d,%d}" % rgb

    def autoset_shape_values(self, el):
        self.autoset_line_pattern(el)
        self.autoset_fill_pattern(el)
        self.autoset_line_color(el)
        self.autoset_fill_color(el)
        self.autoset_line_thickness(el)


class ModelicaEllipse(ModelicaElement, GraphicItem, FilledShape):
    def __init__(self, el, n_indent=5, coords=None, strict=False):
        GraphicItem.__init__(self, coords)
        ModelicaElement.__init__(
            self, "Ellipse", el, n_indent, coords=coords, strict=strict
        )

    def add_attributes(self,  el):
        ModelicaElement.add_attributes(self, el)
        self.autoset_rotation_and_origin(el)
        self.autoset_shape_values(el)
        self.autoset_extent(el)
        self.autoset_angles(el)

    def set_angles(self,  startAngle, endAngle):
        self.add_attribute("startAngle", to_s(startAngle))
        self.add_attribute("endAngle", to_s(endAngle))

    def autoset_angles(self, el):
        if tn(el) != "path":
            return
        start = float(get_ns_attribute(el, "sodipodi", "start"))
        end = float(get_ns_attribute(el, "sodipodi", "end"))
        # NOTE: inkscape has clockwise angles
        # Modelica angles are counter-clockwise
        startAngle = 360 - end / np.pi * 180.0
        endAngle = 360 - start / np.pi * 180.0
        if startAngle > endAngle:
            startAngle -= 360
        self.set_angles(startAngle, endAngle)

    def set_extent(self,  x1, y1, x2, y2):
        self.add_attribute(
            "extent", "{{%s,%s},{%s,%s}}" % to_s(x1, y1, x2, y2)
        )

    def find_extent(self,  el):
        tag = tn(el)
        if tag == "circle":
            cx = float(el.get("cx"))
            cy = float(el.get("cy"))
            rx = float(el.get("r"))
            ry = float(el.get("r"))
        elif tag == "ellipse":
            cx = float(el.get("cx"))
            cy = float(el.get("cy"))
            rx = float(el.get("rx"))
            ry = float(el.get("ry"))
        elif tag == "path":
            cx = float(get_ns_attribute(el, "sodipodi", "cx"))
            cy = float(get_ns_attribute(el, "sodipodi", "cy"))
            rx = float(get_ns_attribute(el, "sodipodi", "rx"))
            ry = float(get_ns_attribute(el, "sodipodi", "ry"))
        return [
            self.x_coord(cx-rx), self.y_coord(cy-ry),
            self.x_coord(cx+rx), self.y_coord(cy+ry)
        ]

    def autoset_extent(self,  el):
        ext = self.find_extent(el)
        self.set_extent(*ext)


class ModelicaRectangle(ModelicaElement, GraphicItem, FilledShape):
    def __init__(self, el, n_indent=5, coords=None, strict=False):
        GraphicItem.__init__(self, coords)
        ModelicaElement.__init__(
            self, "Rectangle", el, n_indent=n_indent, coords=coords,
            strict=strict
        )

    def add_attributes(self, el):
        ModelicaElement.add_attributes(self, el)
        self.autoset_rotation_and_origin(el)
        self.autoset_shape_values(el)
        self.autoset_extent(el)
        self.autoset_radius(el)
        # NOT SUPPORTED (Modelica): borderPattern

    def set_extent(self, x1, y1, x2, y2):
        self.add_attribute(
            "extent", "{{%s,%s},{%s,%s}}" % to_s(x1, y1, x2, y2)
        )

    def find_extent(self, el):
        x = float(el.get("x"))
        y = float(el.get("y"))
        w = float(el.get("width"))
        h = float(el.get("height"))
        return [
            self.x_coord(x), self.y_coord(y),
            self.x_coord(x+w), self.y_coord(y+h)
        ]

    def autoset_extent(self, el):
        ext = self.find_extent(el)
        self.set_extent(*ext)

    def autoset_radius(self, el):
        rx = el.get("rx")
        ry = el.get("ry")
        if rx is None and ry is None:
            return
        if rx is None:
            if self.strict:
                raise MoNKError(
                    "rx and ry must be equal (ry was None, but rx was not)"
                )
            rx = 0
        if ry is None:
            if self.strict:
                raise MoNKError(
                    "rx and ry must be equal (rx was None, but ry was not)"
                )
            ry = 0
        rx = float(rx)
        ry = float(ry)
        if self.strict and not np.isclose(rx, ry):
            raise MoNKError(
                "rx and ry must be equal ({} != {})".format(rx, ry)
            )
        if nonzero(rx) and nonzero(ry):
            self.set_radius((rx + ry) / 2.0)

    def set_radius(self, cr):
        self.add_attribute("radius", cr)

    def set_border_pattern(self, bp):
        self.add_attribute("borderPattern", bp)


class ModelicaPath(ModelicaElement, GraphicItem):
    def __init__(self, name, el, n_indent=3, coords=None, strict=False):
        GraphicItem.__init__(self, coords)
        ModelicaElement.__init__(
            self, name, el, n_indent, coords=coords, strict=strict
        )

    def add_attributes(self, el):
        ModelicaElement.add_attributes(self, el)
        self.autoset_rotation_and_origin(el)
        self.autoset_points_and_smooth(el)

    def autoset_points_and_smooth(self, el):
        d = el.get("d")
        points = self.parse_path(d)
        self.set_points(points)
        smoothOps = frozenset("csqtaCSQTA")
        self.set_smooth(len(frozenset(d) & smoothOps) > 0)

    def parse_path(self, d):
        exp = re.compile(r"([a-zA-Z]|(?:-?\d+(?:\.\d+)?(?:e\-?\d+)?))[\s,]*")

        def float_or_self(x):
            try:
                return float(x)
            except ValueError:
                return x
        tokens = [float_or_self(x) for x in exp.findall(d)]
        points = []
        i = 0
        x = 0
        y = 0
        mode = "abs"
        segtype = ""
        width = 2
        while i < len(tokens):
            if isinstance(tokens[i], str):
                segtype = tokens[i]
                i += 1

            if segtype == 'M':  # move to absolute
                x = tokens[i]
                y = tokens[i+1]
                i += 2
                segtype = 'L'
            elif segtype == 'm':  # move to relative
                x += tokens[i]
                y += tokens[i+1]
                i += 2
                segtype = 'l'
            elif segtype == 'L':  # line to absolute
                if len(points) == 0:
                    points.append([x, y])
                x = tokens[i]
                y = tokens[i+1]
                points.append([x, y])
                i += 2
            elif segtype == 'l':  # line to relative
                if len(points) == 0:
                    points.append([x, y])
                x += tokens[i]
                y += tokens[i+1]
                points.append([x, y])
                i += 2
            elif segtype == 'H':  # horizontal line to absolute
                if len(points) == 0:
                    points.append([x, y])
                x = tokens[i]
                points.append([x, y])
                i += 1
            elif segtype == 'h':  # horizontal line to relative
                if len(points) == 0:
                    points.append([x, y])
                x += tokens[i]
                points.append([x, y])
                i += 1
            elif segtype == 'V':  # vertical line to absolute
                if len(points) == 0:
                    points.append([x, y])
                y = tokens[i]
                points.append([x, y])
                i += 1
            elif segtype == 'v':  # vertical line to relative
                if len(points) == 0:
                    points.append([x, y])
                y += tokens[i]
                points.append([x, y])
                i += 1
            elif segtype in ['z', 'Z']:
                pass
            else:
                # TODO handle smooth paths correctly (as far as possible)
                # NOT SUPPORTED: smooth paths
                if self.strict:
                    raise MoNKError("{0} not supported!".format(tokens[i]))
                # abandon path, since it will be messed up anyway
                return []
        return points

    def set_points(self, points):
        corrected = [[self.x_coord(x), self.y_coord(y)] for x, y in points]
        formatted = ["{%s, %s}" % to_s(x, y) for x, y in corrected]
        self.add_attribute("points", "{%s}" % ", ".join(formatted))

    def set_smooth(self, isSmooth):
        if isSmooth:
            self.add_attribute("smooth", "Smooth.Bezier")


class ModelicaPolygon(ModelicaPath, FilledShape):
    def __init__(self, el, n_indent=5, coords=None, strict=False):
        ModelicaPath.__init__(
            self, "Polygon", el, n_indent, coords=coords, strict=strict
        )

    def add_attributes(self, el):
        ModelicaPath.add_attributes(self, el)
        self.autoset_shape_values(el)


class ModelicaLine(ModelicaPath, FilledShape):
    # line is no filled shape, but we need some of the methods
    def __init__(self, el, n_indent=5, coords=None, strict=False):
        ModelicaPath.__init__(
            self, "Line", el, n_indent, coords=coords, strict=strict
        )

    def add_attributes(self, el):
        ModelicaPath.add_attributes(self, el)
        self.autoset_thickness(el)
        self.autoset_pattern(el)
        self.autoset_color(el)
        self.autoset_arrow(el)

    def autoset_thickness(self, el):
        thickness = self.find_line_thickness(el)
        self.set_thickness(thickness)

    def autoset_color(self, el):
        color = self.find_line_color(el)
        if color is not None and color != "{0,0,0}":
            self.set_color(color)

    def autoset_pattern(self, el):
        pattern = self.find_line_pattern(el)
        if pattern != LinePattern.SOLID:
            self.set_pattern(pattern)

    def autoset_arrow(self, el):
        # if there is a marker, we just assume it's an arrow
        # TODO we might try to interpret some of the marker names from inkscape
        arrow_s = get_style_attribute(el, "marker-start")
        arrow_e = get_style_attribute(el, "marker-end")
        if arrow_s is not None or arrow_e is not None:
            self.set_arrow(arrow_s, arrow_e, self.find_line_thickness(el))

    def set_thickness(self, thick):
        if self.coords is not None:
            thick = self.coords.normalize_delta(thick)
            thick = self.scale_thickness(thick)
        self.add_attribute("thickness", to_s(thick))

    def set_pattern(self, pattern):
        self.add_attribute("pattern", pattern)

    def set_color(self, color):
        self.add_attribute("color", color)

    def set_arrow(self, arrow_s, arrow_e, size):
        # TODO we could give some choices here
        arrow_s = "Arrow.Open" if arrow_s is not None else "Arrow.None"
        arrow_e = "Arrow.Open" if arrow_e is not None else "Arrow.None"
        self.add_attribute("arrow", "{%s, %s}" % (arrow_s, arrow_e))
        self.add_attribute("arrowSize", size)


class ModelicaText(ModelicaElement, GraphicItem, FilledShape):
    def __init__(
            self, el, n_indent=5, coords=None, strict=False, extent="normal"
    ):
        self.font_size_mm = None
        if extent == "normal":
            self.autoscale_font = False
            self.zero_width_extent = False
        elif extent == "flow":
            self.autoscale_font = False
            self.zero_width_extent = True
        elif extent == "scaled":
            self.autoscale_font = True
            self.zero_width_extent = False
        else:
            raise MoNKError(
                "text extent mode {} not recognized".format(extent)
            )
        GraphicItem.__init__(self, coords)
        ModelicaElement.__init__(
            self, "Text", el, n_indent, coords=coords, strict=strict
        )

    def add_attributes(self, el):
        ModelicaElement.add_attributes(self, el)
        self.autoset_rotation_and_origin(el)
        self.autoset_shape_values(el)
        self.autoset_text_string(el)
        self.autoset_font(el)
        self.autoset_horizontal_alignment(el)
        self.autoset_extent(el)

    def autoset_shape_values(self, el):
        FilledShape.autoset_shape_values(self, el)
        # modelica uses the line color for text while SVG uses the fill color
        # => switch those
        if "fillColor" in self.data:
            self.data["lineColor"] = self.data["fillColor"]
            del self.data["fillColor"]
        if "fillPattern" in self.data:
            self.data["pattern"] = self.data["fillPattern"].replace(
                "FillPattern", "LinePattern"
            )
            del self.data["fillPattern"]

    def autoset_text_string(self, el):
        if tn(el) == "tspan":
            text = el.text
        else:
            text = "\n".join([
                etree.tostring(c, method="text").decode("UTF-8")
                for c in el.iterchildren()
            ])
        self.set_text_string(text)

    def get_font(self, el):
        if not isinstance(el, etree._Element):
            return [None, None, None]
        style = ""
        f_style = get_style_attribute(el, "font-style")
        f_weight = get_style_attribute(el, "font-weight")
        t_deco = get_style_attribute(el, "text-decoration")
        if f_style == "italic":
            style.append("i")
        if f_weight == "bold":
            style.append("b")
        if t_deco == "underline":
            style.append("u")
        # distinguish between no attributes given and all set to normal
        if f_style is None and f_weight is None and t_deco is None:
            style = None
        fontName = get_style_attribute(el, "font-family")
        fontSize = get_style_attribute(el, "font-size")
        return fontName, self.to_pt(fontSize), style

    def to_pt(self, size_str):
        if size_str is None:
            return None
        exp_match = re.match(r"(-?\d+\.?\d*)([a-zA-Z]*)", size_str)
        if exp_match is None:
            raise ValueError("cannot understand size {0}".format(size_str))
        # modelica coordinates are assumed to be in mm, so we set 1px = 1mm
        number = exp_match.group(1)
        unit = exp_match.group(2)
        return transform_units(float(number), unit, "pt")

    def autoset_font(self, el):
        outerName, outerSize, outerStyle = self.get_font(el)
        innerName, innerSize, innerStyle = self.get_font(el.getchildren()[0])
        fontSize = innerSize or outerSize or 0
        self.font_size_mm = transform_units(fontSize, "pt", "mm")
        if self.autoscale_font:
            fontSize = 0  # reset font size, but keep font_size_mm for extent
        self.set_font(
            innerName or outerName or "Arial",
            fontSize,
            innerStyle or outerStyle or ""
        )

    def autoset_extent(self, el):
        x = float(el.get("x"))
        y = float(el.get("y"))
        # TODO can we do better for the extent? probably not without rendering
        # the text element
        # determine text width and height in number of characters
        text = eval(self.data["textString"])
        text_w = max([len(s) for s in text.split("\n")])
        text_h = len(text.split("\n"))
        # guess how much pixels (or mm) that would be based on font_size
        # designers tend to be obsessed with the golden ratio
        # => we use this value to guess ratio between font size and character
        # advancement (https://medium.com/@zkareemz/golden-ratio-62b3b6d4282a)
        w = text_w * self.font_size_mm * 1/1.618
        # make line height slightly larger than font size
        line_height = self.font_size_mm * 1.1
        # add line spacing after every line
        h = text_h * line_height \
            + text_h * self.font_size_mm * 0.2  # 1.2 line spacing
        baseline_rel = 0.1  # relative position of baseline within line_height
        ha = self.data["horizontalAlignment"]
        if self.zero_width_extent:
            # TODO Modelica spec says that alignment must still be respected
            # but OpenModelica does not seem to do so? => stick with OM for now
            x1 = x
            y1 = y
            x2 = x
            y2 = y + h - (1 - baseline_rel) * line_height
        elif ha == "TextAlignment.Left":
            x1 = x
            y1 = y - (1 - baseline_rel) * line_height
            x2 = x + w
            y2 = y + h - (1 - baseline_rel) * line_height
        elif ha == "TextAlignment.Right":
            x1 = x - w
            y1 = y - (1 - baseline_rel) * line_height
            x2 = x
            y2 = y + h - (1 - baseline_rel) * line_height
        elif ha == "TextAlignment.Center":
            x1 = x - w/2
            y1 = y - w/2 + baseline_rel * line_height
            x2 = x + w/2
            y2 = y + w/2 + baseline_rel * line_height
        self.set_extent(
            self.x_coord(x1), self.y_coord(y1),
            self.x_coord(x2), self.y_coord(y2)
        )

    def autoset_horizontal_alignment(self, el):
        # first try: text-align attribute in <text> element
        alignOuter = get_style_attribute(el, "text-align")
        # override option: text-anchor attribute in <tspan> element
        anchor_to_align = {
            "start": "left", "end": "right", "middle": "center"
        }
        alignInner = get_style_attribute(el.getchildren()[0], "text-anchor")
        if alignInner is not None:
            alignInner = anchor_to_align[alignInner]
        align = alignInner or alignOuter or "left"
        if align != "center":
            self.set_horizontal_alignment(align)

    def set_extent(self, x1, y1, x2, y2):
        self.add_attribute(
            "extent", "{{%s,%s},{%s,%s}}" % to_s(x1, y1, x2, y2)
        )

    def set_text_string(self, s):
        rs = repr(s)
        if rs[0] not in ["'", '"']:
            rs = rs[2:-1]
        else:
            rs = rs[1:-1]
        self.add_attribute("textString", '"'+rs+'"')

    def set_font(self, fontName, fontSize, style):
        styles = {
            'i': "TextStyle.Italic", 'b': "TextStyle.Bold",
            'u': "TextStyle.UnderLine"
        }
        ",".join([styles[x] for x in style])
        if len(style) > 0:
            self.add_attribute("textStyle", "{%s}" % style_string)
        # ignore "default" font names
        if fontName not in ["Arial", "sans-serif"]:
            self.add_attribute("fontName", '"' + fontName + '"')
        # save unnormalized font size to calculate extent later
        if self.coords is not None:
            fontSize = self.coords.normalize_delta(fontSize)
            fontSize = self.scale_thickness(fontSize)
        self.add_attribute("fontSize", to_s(fontSize))

    def set_horizontal_alignment(self, align):
        css_align_to_modelica = {
            "left": "TextAlignment.Left", "right": "TextAlignment.Right",
            "center": "TextAlignment.Center",
            # NOTE: the following definitions are not valid according to the
            # SVG spec, but they occur in inkscape (bug?)
            "start": "TextAlignment.Left", "end": "TextAlignment.Right"
        }
        alignType = css_align_to_modelica[align]
        self.add_attribute("horizontalAlignment", alignType)

    def has_stroke(self):
        return True


if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(
            sys.argv[1:], "m:s:n:t:",
            ["modelname=", "strict=", "normalize_extent=", "text_extent="]
        )
    except getopt.GetoptError as err:
        print(str(err))
        print(
            "usage: python svg2modelica.py [-m modelname] [-s true/false] "
            + "[-n true/false] [-t normal/scaled/flow] filename"
        )
        exit(1)
    strict = False
    modelname = "DummyModel"
    norm_extent = False
    text_extent = "normal"
    for k, v in opts:
        if k in ("-s", "--strict"):
            strict = v in ["true", "True"]
        elif k in ("-m", "--modelname"):
            modelname = v
        elif k in ("-n", "--normalize_extent"):
            norm_extent = v in ["true", "True"]
        elif k in ("-t", "--text_extent"):
            text_extent = v
    fname = args[0]
    parse_svg(
        fname, modelname, strict=strict, normalize_extent=norm_extent,
        text_extent=text_extent
    )
