# encoding: UTF-8
require 'rexml/document'
require 'java'
JOptionPane = javax.swing.JOptionPane

#log messages with JOptionPane
def log x
  JOptionPane.showMessageDialog(nil,x);
end
INDENT = "  "
HEAD = "model DummyModel\n#{$INDENT}annotation(\n"
FOOT = "#{$INDENT});\nend DummyModel;"

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
      return 
    end
  }
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
    inner = ""
    @data.each {|k, v|
      inner += "#{k}= #{v}"
    }
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
  def find_line_color el
    
  end
  def set_fill_color r, g, b
    add_attribute("fillColor","{#{r},#{g},#{b}}")
  end
  def set_line_pattern
end

class ModelicaRectangle < ModelicaElement
  def initialize el
    super("Rectangle",el)
  end
  def add_attributes el
    super
  end
end

parseSVG(ARGV[0])