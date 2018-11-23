import getopt

# note this must be python 2.6, since inkscape ships with this version :/

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
  print("foo %s %s" % (strict, modelname))