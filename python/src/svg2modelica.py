import getopt
import sys

# note this must be python 2.6, since inkscape ships with this version :/

if __name__ == '__main__':
  try:
    optlist, args = getopt.getopt(args, "m:s", ["modelname=", "strict"])
  except getopt.GetoptError as err:
    print(str(err))
    print("usage: python svg2modelica.py [-m modelname] [-s]")
    sys.exit(1)
  desc = "Converts SVG file to Modelica annotation."
  parser = argparse.ArgumentParser(description=desc)
  mhelp = "name of the model (should be the same as output file name)"
  parser.add_argument("-m", "--modelname", help=mhelp)
  shelp = "non-translatable elements will throw an exception " + \
          "instead of being ignored"
  parser.add_argument("--strict", "-s", action="store_true", help=shelp)
  args = parser.parse_args()
  print("foo %s %s" % (args.strict, args.modelname))