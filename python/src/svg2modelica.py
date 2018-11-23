import getopt
import sys
import lxml.etree as etree

inkex_available = True

try:
  import inkex
except:
  inkex_available = False

INDENT = "    "

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
      inner += (","+line_delim).join(self.elems)
      if len(self.data) > 0:
        inner += ","
      inner += line_delim
    inner += (","+line_delim).join(["{0}= {1}".format(k, v) for k, v in self.data])
    inner += "\n"+INDENT*(self.n_indent-1)
    res = "{0}({1})".format(self.name, inner)
    return res

class ModelicaIcon(ModelicaElement):
  def __init__(self, doc, nIndent=3):
    super(ModelicaIcon, self).__init__("Icon", doc, nIndent)
  def add_attributes(self, doc):
    pass
    #self.add_element(ModelicaCoordinateSystem.new(doc.root,nIndent=@nIndent+1))
    #self.add_attribute("graphics",ModelicaGraphicsContainer.new(doc,nIndent=@nIndent+1))

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
