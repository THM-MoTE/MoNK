import getopt
import sys
import lxml.etree as etree
import re

inkex_available = True

try:
  import inkex
except:
  inkex_available = False

INDENT = "    "

re_to_f = re.compile(r"(\d+)[^\d]*")

def to_f(s):
  return float(re.match(re_to_f, s).group(1))

# note this must be python 2.6, since inkscape ships with this version :/

def parse_svg(fname, modelname, strict=False):
  with open(fname, "rb") as f:
    parser = etree.XMLParser(encoding="utf-8")
    document = etree.parse(f, parser=parser)
  res =   "model {1}\n" \
        + "{0}annotation(\n" \
        + "{0}{0}{2}\n" \
        + "{0});\n" \
        + "end {1};"
  main_icon = ModelicaIcon(document)
  print(res.format(INDENT, modelname, main_icon))

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
    print(self.data)
    inner += (","+line_delim).join(["{0}= {1}".format(k, v) for k, v in self.data.items()])
    inner += "\n"+INDENT*(self.n_indent-1)
    res = "{0}({1})".format(self.name, inner)
    return res

class ModelicaIcon(ModelicaElement):
  def __init__(self, doc, n_indent=3):
    super(ModelicaIcon, self).__init__("Icon", doc, n_indent)
  def add_attributes(self, doc):
    self.add_element(ModelicaCoordinateSystem(doc.getroot(),n_indent=self.n_indent+1))
    #self.add_attribute("graphics",ModelicaGraphicsContainer.new(doc,n_indent=@n_indent+1))


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
