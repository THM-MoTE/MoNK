# encoding: UTF-8
require 'rexml/document'
require 'java'
require 'matrix'
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
  models << ModelicaIcon.new(xml)
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
  def initialize name, el, nIndent = 3
    @name = name
    @data = {}
    @elems = []
    @nIndent = nIndent
    add_attributes el
  end
  def add_attribute key, value
    @data[key] = value
  end
  def add_element modelicaEl
    @elems << modelicaEl
  end
  def add_attributes el
    #add_attribute("fillPattern", "solid")
  end
  def to_s
    inner = "\n"+INDENT*@nIndent
    if not @elems.empty?
      inner += @elems.join(",\n"+INDENT*@nIndent)
      if not @data.empty?
        inner += ","
      end
      inner += "\n"+INDENT*@nIndent
    end
    inner += @data.to_a.collect{|x| "#{x[0]}= #{x[1]}"}.join(",\n"+INDENT*@nIndent)
    inner += "\n"+INDENT*(@nIndent-1)
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
  def autoset_rotation_and_origin el
    att = el.attributes["transform"]
    exp = %r{
      \s*matrix\s*
      \(
      \s*(-?\d+\.?\d*)\s*,
      \s*(-?\d+\.?\d*)\s*,
      \s*(-?\d+\.?\d*)\s*,
      \s*(-?\d+\.?\d*)\s*,
      \s*(-?\d+\.?\d*)\s*,
      \s*(-?\d+\.?\d*)\s*
      \)\s*
    }x
    match = exp.match(att)
    #TODO support for everything but skew could possibliy be added later
    #NOT SUPPORTED: any tranformation including multiple matrix() definitions or
    #instances of translate(), scale(), rotate(), skewX() or skewY()
    if match == nil
      set_origin(0,0)
      set_rotation(0)
      return
    end
    cols = []
    cols << [match[1].to_f,match[2].to_f,0]
    cols << [match[3].to_f,match[4].to_f,0]
    cols << [match[5].to_f,match[6].to_f,1]
    #svg matrix() describes a transformation from the object coordinate system
    #BACK to the coordinate system of the container => invert matrix
    mat = Matrix.columns(cols).inverse
    #to convert the matrix back to angle+origin notation needed for modelica
    #we pass the points (0,0) and (0,1) through the matrix
    p1 = mat * Matrix.columns([[0,0,1]])
    p2 = mat * Matrix.columns([[0,1,1]])
    #assuming that the result of the transform can be expressed as a translation
    #followed by a rotation, one can build a system of linear equations to find
    #the sine (s) and cosine(c) of the rotation as well as the translation vector
    #(tx,ty). The assignments below reflect the resulting equations
    x1 = p1[0,0]; y1 = p1[1,0]
    x2 = p2[0,0]; y2 = p2[1,0]
    s = x2 - x1
    c = y2 - y1
    ty = s*x1 + c*y1
    tx = c == 0 ? (c*ty-y1)*1.0/s : (x1-s*ty)*1.0/c
    puts s,c,tx,ty
    set_origin(tx,ty)
    set_rotation(Math.atan2(s,c)/Math::PI*180)
  end
end

module FilledShape
  def set_line_color r, g, b
    add_attribute("lineColor","{#{r},#{g},#{b}}")
  end
  def autoset_line_color el
    lc = find_line_color(el)
    add_attribute("lineColor",lc) if lc != nil
  end
  def find_line_color el
    att = get_style_attribute(el,"stroke")
    attribute_value_to_color(att)
  end
  def attribute_value_to_color att
    return nil if att == nil
    return css_hex_to_modelica(att) if att.start_with? "#"
    return css_rgb_to_modelica(att) if att.start_with? "rgb"
    #NOT SUPPORTED: none, currentColor, inherit, url(), css color names
    return nil
  end
  def set_fill_color r, g, b
    add_attribute("fillColor","{#{r},#{g},#{b}}")
  end
  def find_fill_color el
    att = get_style_attribute(el,"fill")
    attribute_value_to_color(att)
  end
  def autoset_fill_color el
    fc = find_fill_color(el)
    add_attribute("fillColor",fc) if fc != nil
  end
  def set_line_pattern lp
    add_attribute("pattern",lp)
  end
  def find_line_pattern el
    att = get_style_attribute(el,"stroke")
    return LinePattern::NONE if att == "none"
    #NOT SUPPORTED: Dash, Dot, DashDot, DashDotDot, svg css stroke-dasharray and stroke-dashoffset values
    return LinePattern::SOLID
  end
  def autoset_line_pattern el
    add_attribute("pattern",find_line_pattern(el))
  end
  def set_fill_pattern lp
    add_attribute("fillPattern",lp)
  end
  def find_fill_pattern el
    att = get_style_attribute(el,"fill")
    return FillPattern::NONE if att == "none"
    #NOT SUPPORTED (modelica): Horizontal Vertical Cross Forward Backward CrossDiag HorizontalCylinder VerticalCylinder Sphere
    #NOT SUPPORTED (svg): css fill-rule and fill-opacity
    return FillPattern::SOLID
  end
  def autoset_fill_pattern el
    add_attribute("fillPattern",find_fill_pattern(el))
  end
  def set_line_thickness x
    add_attribute("lineThickness",x)
  end
  def find_line_thickness el
    att = get_style_attribute(el,"stroke-width")
    #NOT SUPPORTED (svg): inherit, percentage (need viewport info for that)
    return nil if att == nil
    return 1.0 if att.include? "%" or att == "inherit"
    return att.to_f
  end
  def autoset_line_thickness el
    val = find_line_thickness(el)
    return if val == nil
    set_line_thickness(val)
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
  def autoset_shape_values el
    autoset_line_color(el)
    autoset_fill_color(el)
    autoset_line_pattern(el)
    autoset_fill_pattern(el)
    autoset_line_thickness(el)
  end
end

class ModelicaIcon < ModelicaElement
  def initialize doc, nIndent=3
    super("Icon",doc,nIndent)
  end
  def add_attributes doc
    add_element(ModelicaCoordinateSystem.new(doc.root,nIndent=@nIndent+1))
    add_attribute("graphics",ModelicaGraphicsContainer.new(doc,nIndent=@nIndent+1))
  end
end

class ModelicaGraphicsContainer
  def initialize doc, nIndent = 4
    @nIndent = nIndent
    @elems = []
    add_elements(doc)
  end
  def add_elements doc
    doc.elements.each("//rect") {|c| 
      @elems << ModelicaRectangle.new(c,@nIndent+1)
    }
  end
  def add_element modelicaEl
    @elems << modelicaEl
  end
  def to_s
    inner = "\n"+INDENT*@nIndent
    inner += @elems.join(",\n"+INDENT*@nIndent)
    inner += "\n"+INDENT*(@nIndent-1)
    return "{#{inner}}"
  end
end

class ModelicaCoordinateSystem < ModelicaElement
  def initialize svg, nIndent = 4
    super("coordinateSystem",svg,nIndent=nIndent)
  end
  def add_attributes svg
    add_attribute("preserveAspectRatio","false")
    autoset_extent(svg)
  end
  def set_extent x1,y1,x2,y2
    add_attribute("extent","{{#{x1},#{y1}},{#{x2},#{y2}}}")
  end
  def find_extent svg
    w = svg.attributes["width"].to_f
    h = svg.attributes["height"].to_f
    return [0,0,w,h]
  end
  def autoset_extent svg
    ext = find_extent(svg)
    set_extent(ext[0],ext[1],ext[2],ext[3])
  end
end

class ModelicaRectangle < ModelicaElement
  include GraphicItem
  include FilledShape
  def initialize el, nIndent = 5
    super("Rectangle",el,nIndent=nIndent)
  end
  def add_attributes el
    super
    autoset_rotation_and_origin(el)
    autoset_shape_values(el)
    autoset_extent(el)
    #TODO corner radius
    #UNSUPPORTED ATTRIBUTES: borderPattern
  end
  def set_extent x1, y1, x2, y2
    add_attribute("extent","{{#{x1},#{y1}},{#{x2},#{y2}}}")
  end
  def find_extent el
    #TODO fix coordinate system
    x = el.attributes["x"].to_f
    y = el.attributes["y"].to_f
    w = el.attributes["width"].to_f
    h = el.attributes["height"].to_f
    return [x,y,x+w,y+w]
  end
  def autoset_extent el
    ext = find_extent(el)
    set_extent(ext[0],ext[1],ext[2],ext[3])
  end
  def set_corner_radius cr
    add_attribute("radius",cr)
  end
  def set_border_pattern bp
    add_attribute("borderPattern",bp)
  end
end

parseSVG(ARGV[0])

class Test
  include GraphicItem
  include FilledShape
end

#t = Test.new
#puts t.css_rgb_to_modelica("rgb ( 0%  , 90% ,100%)")

