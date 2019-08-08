import getopt
import sys
import lxml.etree as etree
import re
import numpy as np

inkex_available = True

try:
  import inkex
except:
  inkex_available = False

def identity(x):
  return x

# note: this must be python 2.6, since inkscape ships with this version :/
# TODO: normalize outer extent to {{-100, -100}, {100, 100}}

INDENT = "    "

re_to_f = re.compile(r"(\d+)[^\d]*")

def to_f(s):
  return float(re.match(re_to_f, s).group(1))

def tn(el):
  return etree.QName(el.tag).localname

def parse_svg(fname, modelname, strict=False, normalize_extent=False):
  with open(fname, "rb") as f:
    parser = etree.XMLParser(encoding="utf-8", ns_clean=True)
    document = etree.parse(f, parser=parser)
  res =   "model {1}\n" \
        + "{0}annotation(\n" \
        + "{0}{0}{2}\n" \
        + "{0});\n" \
        + "end {1};"
  main_icon = ModelicaIcon(document, normalize_extent=normalize_extent)
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
    "pt" : 25.4/72, "px" : 1, "pc" : 12, "mm" : 1,
    "cm" : 10, "in" : 25.4
  }
  return value * to_mm_factors[from_unit] / to_mm_factors[to_unit]

class ModelicaElement(object):
  def __init__(self, name, el, n_indent=3, coords=None):
    self.name = name
    self.data = {}
    self.elems = []
    self.n_indent = n_indent
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
    inner += (","+line_delim).join(["{0}= {1}".format(k, v) for k, v in self.data.items()])
    inner += "\n"+INDENT*(self.n_indent-1)
    res = "{0}({1})".format(self.name, inner)
    return res

class ModelicaIcon(ModelicaElement):
  def __init__(self, doc, n_indent=3, normalize_extent=False, coords=None):
    # needs to be initialized first, because add_attribute is called in
    # superclass constructor
    self.norm_extent = normalize_extent
    ModelicaElement.__init__(self, "Icon", doc, n_indent, coords=coords)
  def add_attributes(self, doc):
    coords = ModelicaCoordinateSystem(doc.getroot(),n_indent=self.n_indent+1, normalize_extent=self.norm_extent)
    self.add_element(coords)
    self.add_attribute("graphics",ModelicaGraphicsContainer(doc,n_indent=self.n_indent+1, coords=coords))


class ModelicaCoordinateSystem(ModelicaElement):
  def __init__(self, svg, n_indent = 4, normalize_extent=False):
    # needs to be set first to be available in add_attributes
    self.norm_extent = normalize_extent
    ModelicaElement.__init__(
      self, "coordinateSystem",svg,n_indent=n_indent
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
  def add_attributes(self, svg):
    self.add_attribute("preserveAspectRatio","false")
    self.autoset_extent(svg)
  def set_extent(self,x1,y1,x2,y2):
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
    self.add_attribute("extent","{{%d,%d},{%d,%d}}" % (x1, y1, x2, y2))
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
      return [0,-h,w,0]
  def autoset_extent(self, svg):
    ext = self.find_extent(svg)
    self.set_extent(*ext)

class ModelicaGraphicsContainer(object):
  def __init__(self, doc, n_indent = 4, coords=None):
    self.n_indent = n_indent
    self.elems = []
    self.coords = coords
    self.add_descendants(doc.getroot())
  def to_modelica(self, el):
    tag = tn(el)
    if not isinstance(el, etree._Element):
      return None
    if tag == "rect":
      return ModelicaRectangle(el, self.n_indent+1, coords=self.coords)
    elif tag == "path":
      fill = get_style_attribute(el, "fill")
      if get_ns_attribute(el, "sodipodi", "type") == "arc":
        return ModelicaEllipse(el, self.n_indent+1, coords=self.coords)
      elif re.match(r".*[zZ]\s*$", el.get("d")):
        return ModelicaPolygon(el, self.n_indent+1, coords=self.coords)
      elif fill is not None and (fill != "none"):
        return ModelicaPolygon(el, self.n_indent+1, coords=self.coords)
      else:
        return ModelicaLine(el, self.n_indent+1, coords=self.coords)
    elif tag == "circle":
      return ModelicaEllipse(el, self.n_indent+1, coords=self.coords)
    elif tag == "ellipse":
      return ModelicaEllipse(el, self.n_indent+1, coords=self.coords)
    elif tag == "text":
      return ModelicaText(el, self.n_indent+1, coords=self.coords)
    else:
      return None # TODO this is where we have to decide if we want errors
    # TODO (nice to have) support bitmap images
  def add_descendants(self, el):
    for c in el.iterchildren():
      m = self.to_modelica(c)
      # exclude definitions, metadata and text nodes
      if m is None and isinstance(c, etree._Element) and tn(c) not in ["defs", "metadata"]:
        self.add_descendants(c)
      elif m is not None:
        self.elems.append(m)
  def add_element(self, modelica_el):
    self.elems.append(modelica_el)
  def __str__(self):
    inner = "\n"+INDENT*self.n_indent
    inner += (",\n"+INDENT*self.n_indent).join([str(x) for x in self.elems])
    inner += "\n"+INDENT*(self.n_indent-1)
    return "{" + inner + "}"

class LinePattern:
  NONE = "LinePattern.None"
  SOLID = "LinePattern.Solid"
  DASH = "LinePattern.Dash"
  DOT = "LinePattern.Dot"
  DASH_DOT = "LinePattern.DashDot"
  DASH_DOT_DOT  = "LinePattern.DashDotDot"
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
    res = x
    if self.coords is not None:
      res = self.coords.normalize_x(res)
    res += self.offset_x
    return res
  def y_coord(self, y):
    res = -y
    if self.coords is not None:
      res = self.coords.normalize_y(res)
    res += self.offset_y
    return res
  def set_origin(self, x, y):
    y = -y
    if self.coords is not None:
      x = self.coords.normalize_x(x)
      y = self.coords.normalize_y(y)
    self.offset_x = -x
    self.offset_y = -y
    self.add_attribute("origin","{%d,%d}" % (x, y))
  def set_rotation(self, deg):
    self.add_attribute("rotation",deg)
  def get_matrix(self, el):
    # get the transformation matrix for this element
    if el is None:
      return np.eye(3, dtype="float32")
    mpar = self.get_matrix(el.getparent())
    mel = self.parse_transform(el.get("transform"))
    return np.dot(mpar, mel)
  def parse_transform(self, transform):
    # TODO does not handle multiple transforms in one string
    # NOT SUPPORTED: does not handle skew and scale
    if transform is None:
      return np.eye(3, dtype="float32")
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
        t = self.parse_transform("translate({1}, {2})".format(g[1], g[2]))
        r = self.parse_transform("rotate({1})".format(g[0]))
        ti = self.parse_transform("translate({1}, {2})".format(-g[1], -g[2]))
        mat =  np.dot(np.dot(t, r), ti)
      else:
        alpha = float(g[0]) / 180.0 * np.pi
        mat = np.array([
          [np.cos(alpha), -np.sin(alpha), 0],
          [np.sin(alpha), np.cos(alpha) , 0],
          [0, 0, 1]
        ])
    else:  
      # ignore what we cannot handle
      mat = np.eye(3, dtype="float32")
      
    flip = np.array([[1,0,0],[0,-1,0],[0,0,1]], dtype="float32")
    # flip coordinates, apply matrix to flipped points and flip back again
    # this is required because the y axis of the SVG coordinate system starts
    # at the top but the y axis of modelica starts at the bottom of the icon
    return np.dot(np.dot(flip, mat), flip)
  def decompose_matrix(self, mat):
    # decompose transformation matrix to angle + origin form
    tx = mat[0,2]
    ty = mat[1,2]
    # remove translational component to obtain rotation matrix
    rmat = mat - np.array([[0,0,tx],[0,0,ty],[0,0,0]], dtype="float32")
    # pass vector [1,0] through the rotation matrix
    rotated_x = np.dot(rmat, np.array([[1],[0],[1]]))
    # determine angle between starting vector and rotated vector
    alpha = np.arctan2(rotated_x[1,0],rotated_x[0,0])
    return tx, ty, alpha
  def autoset_rotation_and_origin(self, el):
    mat = self.get_matrix(el)
    tx, ty, alpha = self.decompose_matrix(mat)
    self.set_origin(tx,ty)
    self.set_rotation(alpha/np.pi*180)

class FilledShape(object):
  def set_line_color(self, r, g, b):
    self.add_attribute("lineColor","{%d,%d,%d}" % (r, g, b))
  def autoset_line_color(self, el):
    lc = self.find_line_color(el)
    if lc is not None:
      self.add_attribute("lineColor", lc)
  def find_line_color(self, el):
    att = get_style_attribute(el, "stroke")
    self.attribute_value_to_color(att)
  def attribute_value_to_color(self, att):
    if att is None:
      return None
    if att.startswith("#"):
      return self.css_hex_to_modelica(att)
    if att.startswith("rgb"):
      return self.css_rgb_to_modelica(att)
    #NOT SUPPORTED: none, currentColor, inherit, url(), css color names
    return None
  def set_fill_color(self, r, g, b):
    self.add_attribute("fillColor","{%d,%d,%d}" % (r, g, b))
  def find_fill_color (self, el):
    att = get_style_attribute(el,"fill")
    return self.attribute_value_to_color(att)
  def autoset_fill_color (self, el):
    fc = self.find_fill_color(el)
    if fc is not None:
      self.add_attribute("fillColor",fc)
  def set_line_pattern (self, lp):
    self.add_attribute("pattern",lp)
  def find_line_pattern (self, el):
    att = get_style_attribute(el,"stroke")
    if att == "none":
      return LinePattern.NONE
    #NOT SUPPORTED: Dash, Dot, DashDot, DashDotDot, svg css stroke-dasharray and stroke-dashoffset values
    return LinePattern.SOLID
  def autoset_line_pattern (self, el):
    self.add_attribute("pattern",self.find_line_pattern(el))
  def set_fill_pattern (self, lp):
    self.add_attribute("fillPattern",lp)
  def find_fill_pattern (self, el):
    att = get_style_attribute(el,"fill")
    if att == "none":
      return FillPattern.NONE
    #NOT SUPPORTED (modelica): Horizontal Vertical Cross Forward Backward CrossDiag HorizontalCylinder VerticalCylinder Sphere
    #NOT SUPPORTED (svg): css fill-rule and fill-opacity
    return FillPattern.SOLID
  def autoset_fill_pattern (self, el):
    self.add_attribute("fillPattern",self.find_fill_pattern(el))
  def set_line_thickness (self, x):
    self.add_attribute("lineThickness",x)
  def find_line_thickness (self, el):
    att = get_style_attribute(el,"stroke-width")
    if att is None:
      return None
    if "%" in att or att == "inherit":
      #NOT SUPPORTED (svg): inherit, percentage (need viewport info for that)
      return 1.0
    return to_f(att)
  def autoset_line_thickness (self, el):
    val = self.find_line_thickness(el)
    if val is not None:
      self.set_line_thickness(val)
  def css_hex_to_modelica (self, hexstr):
    hexstr = hexstr[1:]
    sz = 2 if len(hexstr) > 3 else 1
    return "{%d,%d,%d}" % tuple([int(hexstr[i*sz:i*sz+sz], 16) for i in range(3)])
  def css_rgb_to_modelica (self, rgbstr):
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
  def autoset_shape_values (self, el):
    self.autoset_line_color(el)
    self.autoset_fill_color(el)
    self.autoset_line_pattern(el)
    self.autoset_fill_pattern(el)
    self.autoset_line_thickness(el)

class ModelicaEllipse(ModelicaElement, GraphicItem, FilledShape):
  def __init__(self, el, n_indent = 5, coords=None):
    GraphicItem.__init__(self, coords)
    ModelicaElement.__init__(self, "Ellipse", el, n_indent, coords=coords)
  def add_attributes (self,  el):
    ModelicaElement.add_attributes(self, el)
    self.autoset_rotation_and_origin(el)
    self.autoset_shape_values(el)
    self.autoset_extent(el)
    self.autoset_angles(el)
  def set_angles (self,  startAngle, endAngle):
    self.add_attribute("startAngle", startAngle)
    self.add_attribute("endAngle", endAngle)
  def autoset_angles (self, el):
    if tn(el) != "path":
      return
    start = float(get_ns_attribute(el, "sodipodi", "start"))
    end = float(get_ns_attribute(el, "sodipodi", "end"))
    # NOTE: inkscape has clockwise angles, Modelica angles are counter-clockwise
    startAngle = 360 - end / np.pi * 180.0
    endAngle = 360 - start / np.pi * 180.0
    if startAngle > endAngle:
      startAngle -= 360
    self.set_angles(startAngle, endAngle)
  def set_extent (self,  x1, y1, x2, y2):
    self.add_attribute("extent","{{%d,%d},{%d,%d}}" % (x1, y1, x2, y2))
  def find_extent (self,  el):
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
      self.x_coord(cx-rx),self.y_coord(cy-ry),
      self.x_coord(cx+rx),self.y_coord(cy+ry)
    ]
  def autoset_extent (self,  el):
    ext = self.find_extent(el)
    self.set_extent(*ext)

class ModelicaRectangle(ModelicaElement, GraphicItem, FilledShape):
  def __init__(self, el, n_indent=5, coords=None):
    GraphicItem.__init__(self, coords)
    ModelicaElement.__init__(self, "Rectangle",el,n_indent=n_indent,coords=coords)
  def add_attributes(self, el):
    ModelicaElement.add_attributes(self, el)
    self.autoset_rotation_and_origin(el)
    self.autoset_shape_values(el)
    self.autoset_extent(el)
    #TODO corner radius
    #UNSUPPORTED ATTRIBUTES: borderPattern
  def set_extent(self, x1, y1, x2, y2):
    self.add_attribute("extent","{{%d,%d},{%d,%d}}" % (x1, y1, x2, y2))
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
  def set_corner_radius(self, cr):
    self.add_attribute("radius",cr)
  def set_border_pattern(self, bp):
    self.add_attribute("borderPattern",bp)


class ModelicaPath(ModelicaElement, GraphicItem):
  def __init__(self, name, el, n_indent=3, coords=None):
    GraphicItem.__init__(self, coords)
    ModelicaElement.__init__(self, name, el, n_indent, coords=coords)
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
    exp = re.compile(r"([a-zA-Z]|(?:-?\d+\.?\d*))[\s,]*")
    def float_or_self(x):
      try:
        return float(x)
      except:
        return x
    tokens = [float_or_self(x) for x in exp.findall(d)]
    points = []
    i = 0
    x = 0
    y = 0
    mode = "abs"
    width = 2
    while i < len(tokens):
      if tokens[i] == 'M': # move to absolute
        x = tokens[i+1]
        y = tokens[i+2]
        mode = "abs"
        width = 2
        i += 3
      elif tokens[i] == 'm': # move to relative
        x += tokens[i+1]
        y += tokens[i+2]
        mode = "rel"
        width = 2
        i += 3
      elif tokens[i] == 'L': # line to absolute
        if len(points) == 0:
          points.append([x, y])
        x = tokens[i+1]
        y = tokens[i+2]
        points.append([x, y])
        mode = "abs"
        width = 2
        i += 3
      elif tokens[i] == 'l': # line to relative
        if len(points) == 0:
          points.append([x, y])
        x += tokens[i+1]
        y += tokens[i+2]
        points.append([x, y])
        mode = "rel"
        width = 2
        i += 3
      elif tokens[i] in ['z','Z']:
        i += 1
      elif isinstance(tokens[i], float):
        if len(points) == 0:
          points.append([x, y])
        if mode == "abs":
          x = tokens[i]
          y = tokens[i+1]
        else:
          x += tokens[i]
          y += tokens[i+1]
        points.append([x, y])
        i += width
      else:
        # TODO handle smooth paths correctly (as far as possible)
        # UNSUPPORTED: smooth paths
        raise ValueError("{0} not supported!".format(tokens[i]))
    return points
  def set_points(self, points):
    corrected = [[self.x_coord(x), self.y_coord(y)] for x, y in points]
    formatted = ["{%d, %d}" % (x, y) for x, y in corrected]
    self.add_attribute("points","{%s}" % ", ".join(formatted))
  def set_smooth(self, isSmooth):
    if isSmooth:
      self.add_attribute("smooth", "Smooth.Bezier")

class ModelicaPolygon(ModelicaPath, FilledShape):
  def __init__(self, el, n_indent = 5, coords=None):
    ModelicaPath.__init__(self, "Polygon", el, n_indent, coords=coords)
  def add_attributes(self, el):
    ModelicaPath.add_attributes(self, el)
    self.autoset_shape_values(el)

class ModelicaLine(ModelicaPath, FilledShape):
  # line is no filled shape, but we need some of the methods
  def __init__(self, el, n_indent = 5, coords=None):
    ModelicaPath.__init__(self, "Line", el, n_indent, coords=coords)
  def add_attributes(self, el):
    ModelicaPath.add_attributes(self, el)
    self.autoset_thickness(el)
    self.autoset_pattern(el)
    self.autoset_color(el)
    self.autoset_arrow(el)
  def autoset_thickness(self,el):
    thickness = self.find_line_thickness(el)
    self.set_thickness(thickness)
  def autoset_color(self,el):
    color = self.find_line_color(el)
    if color is not None:
      self.set_color(color)
  def autoset_pattern(self,el):
    pattern = self.find_line_pattern(el)
    self.set_pattern(pattern)
  def autoset_arrow(self,el):
    # if there is a marker, we just assume it's an arrow
    # TODO we might try to interpret some of the marker names from inkscape
    arrow_s = get_style_attribute(el,"marker-start")
    arrow_e = get_style_attribute(el,"marker-end")
    if arrow_s is not None or arrow_e is not None:
      self.set_arrow(arrow_s, arrow_e, self.find_line_thickness(el))
  def set_thickness(self, thick):
    self.add_attribute("thickness", thick)
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
  def __init__(self, el, n_indent = 5, coords=None):
    GraphicItem.__init__(self, coords)
    ModelicaElement.__init__(self, "Text", el, n_indent, coords=coords)
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
    self.data["lineColor"] = self.data["fillColor"]
    self.data["pattern"] = self.data["fillPattern"].replace("FillPattern","LinePattern")
    del self.data["fillColor"]
    del self.data["fillPattern"]
  def autoset_text_string(self, el):
    if tn(el) == "tspan":
      text = el.text
    else:
      text = "\n".join([etree.tostring(c, method="text").decode("UTF-8") for c in el.iterchildren()])
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
    self.set_font(
      innerName or outerName or "Arial",
      innerSize or outerSize or "0",
      innerStyle or outerStyle or ""
    )
  def autoset_extent(self, el):
    x = float(el.get("x"))
    y = float(el.get("y"))
    # TODO can we do better for the extent? probably not without rendering the
    # text element
    # get the calculated font size from our data and transform it to mm
    font_size = float(self.data["fontSize"]) * 25.4/72
    # determine text width and height in number of characters
    text = eval(self.data["textString"])
    text_w = max([len(s) for s in text.split("\n")])
    text_h = len(text.split("\n"))
    # guess how much pixels (or mm) that would be based on font_size
    w = text_w * font_size * 0.5
    h = text_h * font_size + max(0, text_h-1) * font_size * 0.2
    ha = self.data["horizontalAlignment"]
    if ha == "TextAlignment.Left":
      x1 = x
      y1 = y - 0.8 * font_size
      x2 = x + w
      y2 = y + h - 0.8 * font_size
    elif ha == "TextAlignment.Right":
      x1 = x - w
      y1 = y - 0.8 * font_size
      x2 = x
      y2 = y + h - 0.8 * font_size
    elif ha == "TextAlignment.Center":
      x1 = x - w/2
      y1 = y - w/2 + 0.2 * font_size
      x2 = x + w/2
      y2 = y + w/2 + 0.2 * font_size
    self.set_extent(
      self.x_coord(x1), self.y_coord(y1),
      self.x_coord(x2), self.y_coord(y2)
    )
  def autoset_horizontal_alignment(self, el):
    # first try: text-align attribute in <text> element
    alignOuter = get_style_attribute(el, "text-align")
    # override option: text-anchor attribute in <tspan> element
    anchor_to_align = {
      "start" : "left", "end" : "right", "middle" : "center"
    }
    alignInner = get_style_attribute(el.getchildren()[0], "text-anchor")
    if alignInner is not None:
      alignInner = anchor_to_align[alignInner]
    self.set_horizontal_alignment(alignInner or alignOuter or "left")
  def set_extent(self, x1, y1, x2, y2):
    self.add_attribute("extent","{{%d,%d},{%d,%d}}" % (x1, y1, x2, y2))
  def set_text_string(self, s):
    self.add_attribute("textString", '"'+repr(s)[1:-1]+'"')
  def set_font(self, fontName, fontSize, style):
    styles = { 
      'i' : "TextStyle.Italic", 'b' : "TextStyle.Bold",
      'u' : "TextStyle.UnderLine"
    }
    ",".join([styles[x] for x in style])
    if len(style) > 0:
      self.add_attribute("textStyle", "{%s}" % style_string)
    self.add_attribute("fontName", fontName)
    self.add_attribute("fontSize", fontSize)
  def set_horizontal_alignment(self, align):
    css_align_to_modelica = { 
      "left" : "TextAlignment.Left", "right" : "TextAlignment.Right",
      "center" : "TextAlignment.Center",
      # NOTE: the following definitions are not valid according to the SVG spec,
      # but they occur in inkscape (bug?)
      "start" : "TextAlignment.Left", "end" : "TextAlignment.Right"
    }
    alignType = css_align_to_modelica[align]
    self.add_attribute("horizontalAlignment", alignType)


if __name__ == '__main__':
  try:
    opts, args = getopt.getopt(sys.argv[1:], "m:s:n:", ["modelname=", "strict=", "normalize_extent="])
  except getopt.GetoptError as err:
    print(str(err))
    print("usage: python svg2modelica.py [-m modelname] [-s true/false] [-n true/false] filename")
    exit(1)
  strict = False
  modelname = "DummyModel"
  norm_extent = False
  for k, v in opts:
    if k in ("-s", "--strict"):
      strict = bool(v)
    elif k in ("-m", "--modelname"):
      modelname = v
    elif k in ("-n", "--normalize_extent"):
      norm_extent = bool(v)
  fname = args[0]
  parse_svg(fname, modelname, strict=strict, normalize_extent=norm_extent)
