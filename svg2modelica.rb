# encoding: UTF-8
require 'rexml/document'
require 'java'
JOptionPane = javax.swing.JOptionPane

#log messages with JOptionPane
def log x
  JOptionPane.showMessageDialog(nil,x);
end

INDENT = "  "
HEAD = "model DummyModel\n#{INDENT}annotation(\n"
FOOT = "#{INDENT});\nend DummyModel;"

def parseSVG fname
  xml = REXML::Document.new(File.open(fname))
  models = []
  xml.elements.each("//rect") {|c| 
    models << ModelicaRectangle.new(c)
  }
  first = true
  puts HEAD
  print INDENT*2
  puts models.join(",\n"+INDENT*2)
  puts FOOT
end

def get_style_attribute el, name
  el.attributes["style"].split(";").each {|att|
    if att.start_with? (name+":")
      return att[name.length+1..-1]
    end
  }
  return nil
end

class ModelicaElement
  def initialize name, el
    @name = name
    @data = {}
    add_attributes el
  end
  def add_attribute key, value
    @data[key] = value
  end
  def add_attributes el
    add_attribute("fillPattern", "solid")
  end
  def to_s
    inner = "\n"+INDENT*3
    inner += @data.to_a.collect{|x| "#{x[0]}= #{x[1]}"}.join(",\n"+INDENT*3)
    res = "#{@name}(#{inner})"
    return res
  end
end

module LinePattern
  NONE = "LinePattern.None"
  SOLID = "LinePattern.Solid"
  DASH = "LinePattern.Dash"
  DOT = "LinePattern.Dot"
  DASH_DOT = "LinePattern.DashDot"
  DASH_DOT_DOT  = "LinePattern.DashDotDot"
end
module FillPattern
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
end
module BorderPattern
  NONE = "BorderPattern.None"
  RAISED = "BorderPattern.Raised"
  SUNKEN = "BorderPattern.Sunken"
  ENGRAVED = "BorderPattern.Engraved"
end
module Smooth
  NONE = "Smooth.None"
  BEZIER = "Smooth.Bezier"
end

module GraphicItem
  def set_origin x, y
    add_attribute("origin","{#{x},#{y}}")
  end
  def set_rotation deg
    add_attribute("rotation",deg)
  end
end

module FilledShape
  def set_line_color r, g, b
    add_attribute("lineColor","{#{r},#{g},#{b}}")
  end
  def autoset_line_color el
    add_attribute("lineColor",find_line_color(el))
  end
  def find_line_color el
    att = get_style_attribute(el,"stroke")
    attribute_value_to_color(att)
  end
  def attribute_value_to_color att
    return "Black" if att == nil
    return css_hex_to_modelica(att) if att.start_with? "#"
    return css_rgb_to_modelica(att) if att.start_with? "rgb"
    #NOT SUPPORTED: none, currentColor, inherit, url(), css color names
    return "Black"
  end
  def set_fill_color r, g, b
    add_attribute("fillColor","{#{r},#{g},#{b}}")
  end
  def set_line_pattern
    ""
  end
  def css_hex_to_modelica hexstr
    hexstr = hexstr[1..-1]
    sz = hexstr.length > 3 ? 2 : 1
    conv = lambda {|str| (str.slice!(0..sz-1)*(3-sz)).hex}
    r = conv.call(hexstr)
    g = conv.call(hexstr)
    b = conv.call(hexstr)
    return "{#{r},#{g},#{b}}"
  end
  def css_rgb_to_modelica rgbstr
    match = /\s*rgb\s*\(\s*(\d+\%?)\s*,\s*(\d+\%?)\s*,\s*(\d+\%?)\s*\)\s*/.match(rgbstr)
    r = match[1]
    g = match[2]
    b = match[3]
    if r[-1] == "%" 
      r = (r[0..-2].to_i*255.0/100).round
      g = (g[0..-2].to_i*255.0/100).round
      b = (b[0..-2].to_i*255.0/100).round
    else
      r = r.to_i
      g = g.to_i
      b = b.to_i
    end
    return "{#{r},#{g},#{b}}"
  end
end

class ModelicaRectangle < ModelicaElement
  include GraphicItem
  include FilledShape
  def initialize el
    super("Rectangle",el)
  end
  def add_attributes el
    super
    autoset_line_color(el)
  end
end

parseSVG(ARGV[0])

class Test
  include GraphicItem
  include FilledShape
end

#t = Test.new
#puts t.css_rgb_to_modelica("rgb ( 0%  , 90% ,100%)")

