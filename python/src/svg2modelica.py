import getopt
import sys
import lxml.etree as etree

inkex_available = True

try:
  import inkex
except:
  inkex_available = False

# note this must be python 2.6, since inkscape ships with this version :/

def parse_svg(fname, modelname, strict=False):
  with open(fname, "rb") as f:
    parser = etree.XMLParser(encoding="utf-8")
    document = etree.parse(f, parser=parser)
  print(document)

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
