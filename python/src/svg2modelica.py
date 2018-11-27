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

# note: this must be python 2.6, since inkscape ships with this version :/

INDENT = "    "

re_to_f = re.compile(r"(\d+)[^\d]*")

def to_f(s):
  return float(re.match(re_to_f, s).group(1))

def tn(el):
  return etree.QName(el.tag).localname

def parse_svg(fname, modelname, strict=False):
  with open(fname, "rb") as f:
    parser = etree.XMLParser(encoding="utf-8", ns_clean=True)
    document = etree.parse(f, parser=parser)
  res =   "model {1}\n" \
        + "{0}annotation(\n" \
        + "{0}{0}{2}\n" \
        + "{0});\n" \
        + "end {1};"
  main_icon = ModelicaIcon(document)
  print(res.format(INDENT, modelname, main_icon))

def get_style_attribute(el, name):
  if el.get("style") is None:
    return None
  for att in el.get("style").split(";"):
    if att.startswith(name+":"):
      return att[len(name)+1:-1]
  return None

class ModelicaElement(object):
  def __init__(self, name, el, n_indent=3):
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
  def __init__(self, doc, n_indent=3):
    super(ModelicaIcon, self).__init__("Icon", doc, n_indent)
  def add_attributes(self, doc):
    self.add_element(ModelicaCoordinateSystem(doc.getroot(),n_indent=self.n_indent+1))
    self.add_attribute("graphics",ModelicaGraphicsContainer(doc,n_indent=self.n_indent+1))


class ModelicaCoordinateSystem(ModelicaElement):
  def __init__(self, svg, n_indent = 4):
    super(ModelicaCoordinateSystem, self).__init__(
      "coordinateSystem",svg,n_indent=n_indent
    )
    self.px2mm_factor_x = 1
    self.px2mm_factor_y = 1
  def add_attributes(self, svg):
    self.add_attribute("preserveAspectRatio","false")
    self.autoset_extent(svg)
  def set_extent(self,x1,y1,x2,y2):
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
  def __init__(self, doc, n_indent = 4):
    self.n_indent = n_indent
    self.elems = []
    self.add_descendants(doc.getroot())
  def to_modelica(self, el):
    tag = tn(el)
    if not isinstance(el, etree._Element):
      return None
    if tag == "rect":
      return ModelicaRectangle(el, self.n_indent+1)
    elif tag == "path":
      fill = get_style_attribute(el, "fill")
      if el.get("sodipodi:type") == "arc":
        return ModelicaEllipse(el, self.n_indent+1)
      elif re.match(r".*[zZ]\s*$", el.get("d")):
        return ModelicaPolygon(el, self.n_indent+1)
      elif fill is not None and (fill != "none"):
        return ModelicaPolygon(el, self.n_indent+1)
      else:
        return ModelicaLine(el, self.n_indent+1)
    elif tag == "circle":
      return ModelicaEllipse(el, self.n_indent+1)
    elif tag == "ellipse":
      return ModelicaEllipse(el, self.n_indent+1)
    elif tag == "text":
      return ModelicaText(el, self.n_indent+1)
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
  def __init__(*args, **kwargs):
    # empty init method required to allow calls to super() in
    # classes that use this class as one of multiple base classes
    pass
  def x_coord(self, x):
    return x
  def y_coord(self, y):
    return -y
  def set_origin(self, x, y):
    self.add_attribute("origin","{#{x},#{y}}")
  def set_rotation(self, deg):
    self.add_attribute("rotation",deg)
  def get_matrix(self, el):
    # get the transformation matrix for this element
    if el is None:
      return np.eye(3, dtype="float32")
    mpar = self.get_matrix(el.getparent())
    mel = self.parse_transform(el.get("transform"))
    return mpar * mel
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
      g = [float(x) for x in m_rot.groups()]
      if g[1] is not None:
        t = self.parse_transform("translate({1}, {2})".format(g[1], g[2]))
        r = self.parse_transform("rotate({1})".format(g[0]))
        ti = self.parse_transform("translate({1}, {2})".format(-g[1], -g[2]))
        mat =  t.dot(r).dot(ti)
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
    return flip.dot(mat).dot(flip)
  def decompose_matrix(self, mat):
    # decompose transformation matrix to angle + origin form
    tx = mat[0,2]
    ty = mat[1,2]
    # remove translational component to obtain rotation matrix
    rmat = mat - np.array([[0,0,tx],[0,0,ty],[0,0,0]], dtype="float32")
    # pass vector [1,0] through the rotation matrix
    rotated_x = rmat.dot(np.array([[1],[0],[1]]))
    # determine angle between starting vector and rotated vector
    alpha = np.arctan2(rotated_x[1,0],rotated_x[0,0])
    return tx, ty, alpha
  def autoset_rotation_and_origin(self, el):
    mat = self.get_matrix(el)
    tx, ty, alpha = self.decompose_matrix(mat)
    self.set_origin(tx,ty)
    self.set_rotation(alpha/np.pi*180)

class FilledShape(object):
  def __init__(*args, **kwargs):
    # empty init method required to allow calls to super() in
    # classes that use this class as one of multiple base classes
    pass
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
    return float(att)
  def autoset_line_thickness (self, el):
    val = self.find_line_thickness(el)
    if val is not None:
      self.set_line_thickness(val)
  def css_hex_to_modelica (self, hexstr):
    hexstr = hexstr[1:-1]
    sz = 2 if len(hexstr) > 3 else 1
    return "{%d,%d,%d}" % tuple([int(hexstr[i:i+sz], 16) for i in range(3)])
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
  def __init__(self, el, n_indent = 5):
    super(ModelicaEllipse, self).__init__("Ellipse", el, n_indent=n_indent)
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
    startAngle = float(el.get("sodipodi:start")) / np.pi * 180.0
    endAngle = float(el.get("sodipodi:end")) / np.pi * 180.0
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
      cx = float(el.get("sodipodi:cx"))
      cy = float(el.get("sodipodi:cy"))
      rx = float(el.get("sodipodi:rx"))
      ry = float(el.get("sodipodi:ry"))
    return [
      self.x_coord(cx-rx),self.y_coord(cy-ry),
      self.x_coord(cx+rx),self.y_coord(cy+ry)
    ]
  def autoset_extent (self,  el):
    ext = self.find_extent(el)
    self.set_extent(*ext)

if __name__ == '__main__':
  try:
    opts, args = getopt.getopt(sys.argv[1:], "m:s:", ["modelname=", "strict="])
  except getopt.GetoptError as err:
    print(str(err))
    print("usage: python svg2modelica.py [-m modelname] [-s true/false] filename")
    exit(1)
  strict = False
  modelname = "DummyModel"
  for k, v in opts:
    if k in ("-s", "--strict"):
      strict = bool(v)
    elif k in ("-m", "--modelname"):
      modelname = v
  fname = args[0]
  parse_svg(fname, modelname, strict=strict)
