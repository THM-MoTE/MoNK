# encoding: UTF-8
require 'rexml/document'
require 'java'
require 'matrix'
require 'set'
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
  return nil if el.attributes["style"].nil?
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
  def x_coord x
    x
  end
  def y_coord y
    -y
  end
  def set_origin x, y
    add_attribute("origin","{#{x},#{y}}")
  end
  def set_rotation deg
    add_attribute("rotation",deg)
  end
  def get_matrix el
    # get the transformation matrix for this element
    return Matrix.I(3) if el == nil
    mpar = get_matrix(el.parent)
    mel = parse_transform(el.attributes["transform"])
    return mpar * mel
  end
  def parse_transform transform
    # return Matrix.I(3) if transform == nil
    # TODO does not handle multiple transforms in one string
    # NOT SUPPORTED: does not handle skew and scale
    exp_matrix = %r{
      \s*matrix\s*
      \(
        \s*(-?\d+\.?\d*)[\s,]+
        \s*(-?\d+\.?\d*)[\s,]+
        \s*(-?\d+\.?\d*)[\s,]+
        \s*(-?\d+\.?\d*)[\s,]+
        \s*(-?\d+\.?\d*)[\s,]+
        \s*(-?\d+\.?\d*)\s*
      \)\s*
    }x
    exp_translate = %r{
      \s*translate\s*
      \(
        \s*(-?\d+\.?\d*)[\s,]+
        \s*(-?\d+\.?\d*)\s*
      \)
    }x
    exp_rotate = %r{
      \s*rotate\s*
      \(
        \s*(-?\d+\.?\d*)\s*
        (?:[\s,]+
          \s*(-?\d+\.?\d*)[\s,]+
          \s*(-?\d+\.?\d*)\s*
        )?
      \)
    }x
    mat = case transform
      when exp_matrix
        rows = [
          [$1.to_f, $3.to_f, $5.to_f],
          [$2.to_f, $4.to_f, $6.to_f],
          [0, 0, 1]
        ]
        Matrix.rows(rows)
      when exp_translate
        rows = [
          [1, 0, $1.to_f],
          [0, 1, $2.to_f],
          [0, 0, 1]
        ]
        Matrix.rows(rows)
      when exp_rotate
        if $2 then
          return parse_transform("translate(#{$2}, #{$3})") \
               * parse_transform("rotate(#{$1})") \
               * parse_transform("translate(#{-$2.to_f}, #{-$3.to_f})")
        else
          alpha = $1.to_f / 180.0 * Math::PI
          rows = [
            [Math.cos(alpha), -Math.sin(alpha), 0],
            [Math.sin(alpha), Math.cos(alpha) , 0],
            [0, 0, 1]
          ]
          Matrix.rows(rows)
        end
      else
        # ignore what we cannot handle
        Matrix.I(3)
    end
    flip = Matrix.rows([[1,0,0],[0,-1,0],[0,0,1]])
    # flip coordinates, apply matrix to flipped points and flip back again
    # this is required because the y axis of the SVG coordinate system starts
    # at the top but the y axis of modelica starts at the bottom of the icon
    return flip * mat * flip
  end
  def decompose_matrix mat
    # decompose transformation matrix to angle + origin form
    tx = mat[0,2]
    ty = mat[1,2]
    # remove translational component to obtain rotation matrix
    rmat = mat - Matrix.rows([[0,0,tx],[0,0,ty],[0,0,0]])
    # pass vector [1,0] through the rotation matrix
    rotated_x = rmat * Matrix.columns([[1,0,1]])
    # determine angle between starting vector and rotated vector
    alpha = Math.atan2(rotated_x[1,0],rotated_x[0,0]) # - Math.atan2(0,1)
    return tx, ty, alpha
  end
  def autoset_rotation_and_origin el
    mat = get_matrix(el)
    tx, ty, alpha = decompose_matrix(mat)
    set_origin(tx,ty)
    set_rotation(alpha/Math::PI*180)
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
    # TODO respect order of elements
    doc.elements.each("//path") { |c|
      if c.attributes["sodipodi:type"] == "arc" then
        @elems << ModelicaEllipse.new(c,@nIndent+1)
      else
        @elems << ModelicaPolygon.new(c,@nIndent+1)
      end
    }
    doc.elements.each("//circle") { |c|
      @elems << ModelicaEllipse.new(c,@nIndent+1)
    }
    doc.elements.each("//ellipse") { |c|
      @elems << ModelicaEllipse.new(c,@nIndent+1)
    }
    doc.elements.each("//text") { |c|
      @elems << ModelicaText.new(c,@nIndent+1)
    }
    # TODO (nice to have) support bitmap images
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
    return [0,-h,w,0]
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
    x = el.attributes["x"].to_f
    y = el.attributes["y"].to_f
    w = el.attributes["width"].to_f
    h = el.attributes["height"].to_f
    return [x_coord(x),y_coord(y),x_coord(x+w),y_coord(y+h)]
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

class ModelicaEllipse < ModelicaElement
  include GraphicItem
  include FilledShape
  def initialize el, nIndent = 5
    super("Ellipse",el,nIndent=nIndent)
  end
  def add_attributes el
    super
    autoset_rotation_and_origin(el)
    autoset_shape_values(el)
    autoset_extent(el)
    autoset_angles(el)
  end
  def set_angles startAngle, endAngle
    add_attribute("startAngle", startAngle)
    add_attribute("endAngle", endAngle)
  end
  def autoset_angles(el)
    return if el.name != "path"
    startAngle = el.attributes["sodipodi:start"].to_f / Math::PI * 180.0
    endAngle = el.attributes["sodipodi:end"].to_f / Math::PI * 180.0
    set_angles(360-startAngle, 360-endAngle)
  end
  def set_extent x1, y1, x2, y2
    add_attribute("extent","{{#{x1},#{y1}},{#{x2},#{y2}}}")
  end
  def find_extent el
    case el.name
      when "circle"
        cx = el.attributes["cx"].to_f
        cy = el.attributes["cy"].to_f
        rx = el.attributes["r"].to_f
        ry = el.attributes["r"].to_f
      when "ellipse"
        cx = el.attributes["cx"].to_f
        cy = el.attributes["cy"].to_f
        rx = el.attributes["rx"].to_f
        ry = el.attributes["ry"].to_f
      when "path"
        cx = el.attributes["sodipodi:cx"].to_f
        cy = el.attributes["sodipodi:cy"].to_f
        rx = el.attributes["sodipodi:rx"].to_f
        ry = el.attributes["sodipodi:ry"].to_f
    end
    return [x_coord(cx-rx),y_coord(cy-ry),x_coord(cx+rx),y_coord(cy+ry)]
  end
  def autoset_extent el
    ext = find_extent(el)
    set_extent(ext[0],ext[1],ext[2],ext[3])
  end
end

class ModelicaPolygon < ModelicaElement
  include GraphicItem
  include FilledShape
  def initialize el, nIndent = 5
    super("Polygon",el,nIndent=nIndent)
  end
  def add_attributes el
    super
    autoset_rotation_and_origin(el)
    autoset_shape_values(el)
    autoset_points_and_smooth(el)
  end
  def autoset_points_and_smooth(el)
    d = el.attributes["d"]
    points = parse_path(d)
    set_points(points)
    smoothOps = Set.new "csqtaCSQTA".split('')
    set_smooth((Set.new(d.split('')) & smoothOps).size > 0)
  end
  def parse_path d
    exp = /([a-zA-Z]|(?:-?\d+\.?\d*))[\s,]*/
    tokens = d.scan(exp).flatten.map {|x| Float(x) rescue x }
    #tokens[0] = 'M' if tokens[0] == 'm' # first move is always absolute
    points = []
    i = 0
    x = 0
    y = 0
    mode = "abs"
    width = 2
    while i < tokens.size do
      case tokens[i]
        when 'M' # move to absolute
          x = tokens[i+1]
          y = tokens[i+2]
          mode = "abs"
          width = 2
          i += 3
        when 'm' # move to relative
          x += tokens[i+1]
          y += tokens[i+2]
          mode = "rel"
          width = 2
          i += 3
        when 'L' # line to absolute
          points << [x, y] if points.empty?
          x = tokens[i+1]
          y = tokens[i+2]
          points << [x, y]
          mode = "abs"
          width = 2
          i += 3
        when 'l' # line to relative
          points << [x, y] if points.empty?
          x += tokens[i+1]
          y += tokens[i+2]
          points << [x, y]
          mode = "rel"
          width = 2
          i += 3
        when 'z','Z'
          i += 1
        when Float
          points << [x, y] if points.empty?
          if mode == "abs"
            x = tokens[i]
            y = tokens[i+1]
          else
            x += tokens[i]
            y += tokens[i+1]
          end
          points << [x, y]
          i += width
        else
          raise "#{tokens[i]} not supported!"
      end
    end
    return points
  end
  def set_points points
    corrected = points.map { |p| [x_coord(p[0]), y_coord(p[1])] }
    formatted = corrected.map { |x| "{#{x[0]}, #{x[1]}}" }
    add_attribute("points","{#{formatted.join(",")}}")
  end
  def set_smooth isSmooth
    add_attribute("smooth", "Smooth.Bezier") if isSmooth
  end
end

class ModelicaText < ModelicaElement
  include GraphicItem
  include FilledShape
  def initialize el, nIndent = 5
    super("Text",el,nIndent=nIndent)
  end
  def add_attributes el
    super
    autoset_rotation_and_origin(el)
    autoset_shape_values(el)
    autoset_text_string(el)
    autoset_font(el)
    autoset_horizontal_alignment(el)
    autoset_extent(el)
  end
  def autoset_shape_values el
    super
    # modelica uses the line color for text while SVG uses the fill color
    # => switch those
    @data["lineColor"] = @data["fillColor"]
    @data["pattern"] = @data["fillPattern"].sub(/FillPattern/,"LinePattern")
    @data.delete("fillColor")
    @data.delete("fillPattern")
  end
  def autoset_text_string el
    text = if el[0].instance_of? REXML::Text then
      el.get_text.to_s
    else
      el.children.map{|x| x.get_text.to_s}.join("\n")
    end
    set_text_string(text)
  end
  def get_font el
    return [nil, nil, nil] unless el.instance_of? REXML::Element
    style = ""
    f_style = get_style_attribute(el, "font-style")
    f_weight = get_style_attribute(el, "font-weight")
    t_deco = get_style_attribute(el, "text-decoration")
    style << "i" if f_style == "italic"
    style << "b" if f_weight == "bold"
    style << "u" if t_deco == "underline"
    # distinguish between no attributes given and all set to normal
    style = nil if f_style.nil? and f_weight.nil? and t_deco.nil?
    fontName = get_style_attribute(el, "font-family")
    fontSize = get_style_attribute(el, "font-size")
    return fontName, to_pt(fontSize), style
  end
  def to_pt size_str
    return nil unless size_str
    exp_match = /(-?\d+\.?\d*)([a-zA-Z]*)/.match(size_str)
    raise "cannot understand size #{size_str}" unless exp_match
    # modelica coordinates are assumed to be in mm, so we set 1px = 1mm
    factors = { 
      "pt" => 25.4/72, "px" => 1, "pc" => 12, "mm" => 1,
      "cm" => 10, "in" => 25.4
    }
    number = exp_match[1]
    unit = exp_match[2]
    return number.to_f * factors[unit] / factors["pt"]
  end
  def autoset_font el
    outerName, outerSize, outerStyle = get_font(el)
    innerName, innerSize, innerStyle = get_font(el[0])
    set_font(
      innerName || outerName || "Arial",
      innerSize || outerSize || "0",
      innerStyle || outerStyle || ""
    )
  end
  def autoset_extent el
    x = el.attributes["x"].to_f
    y = el.attributes["y"].to_f
    # TODO can we do better for the extent? probably not without rendering the
    # text element
    # get the calculated font size from our data and transform it to mm
    font_size = @data["fontSize"].to_f * 25.4/72
    # determine text width and height in number of characters
    text = eval(@data["textString"])
    text_w = text.split("\n").map{|x| x.size}.max
    text_h = text.split("\n").size
    # guess how much pixels (or mm) that would be based on font_size
    w = text_w * font_size * 0.5
    h = text_h * font_size + [0, text_h-1].max * font_size * 0.2
    case @data["horizontalAlignment"]
      when "TextAlignment.Left"
        x1 = x
        y1 = y - 0.8 * font_size
        x2 = x + w
        y2 = y + h - 0.8 * font_size
      when "TextAlignment.Right"
        x1 = x - w
        y1 = y - 0.8 * font_size
        x2 = x
        y2 = y + h - 0.8 * font_size
      when "TextAlignment.Center"
        x1 = x - w/2
        y1 = y - w/2 + 0.2 * font_size
        x2 = x + w/2
        y2 = y + w/2 + 0.2 * font_size
    end
    set_extent(x_coord(x1), y_coord(y1), x_coord(x2), y_coord(y2))
  end
  def autoset_horizontal_alignment el
    # first try: text-align attribute in <text> element
    alignOuter = get_style_attribute(el, "text-align")
    # override option: text-anchor attribute in <tspan> element
    anchor_to_align = {
      "start" => "left", "end" => "right", "middle" => "center"
    }
    alignInner = get_style_attribute(el[0], "text-anchor")
    alignInner = anchor_to_align[alignInner]
    set_horizontal_alignment(alignInner || alignOuter || "left")
  end
  def set_extent x1, y1, x2, y2
    add_attribute("extent","{{#{x1},#{y1}},{#{x2},#{y2}}}")
  end
  def set_text_string str
    add_attribute("textString", str.inspect)
  end
  def set_font fontName, fontSize, style
    styles = { 
      :i => "TextStyle.Italic", :b => "TextStyle.Bold",
      :u => "TextStyle.UnderLine"
    }
    style_string = style.split("").map{|x| styles[x]}.join(",")
    add_attribute("textStyle", "{#{style_string}}") unless style.empty?
    add_attribute("fontName", fontName)
    add_attribute("fontSize", fontSize)
  end
  def set_horizontal_alignment align
    css_align_to_modelica = { 
      "left" => "TextAlignment.Left", "right" => "TextAlignment.Right",
      "center" => "TextAlignment.Center",
      # NOTE: the following definitions are not valid according to the SVG spec,
      # but they occur in inkscape (bug?)
      "start" => "TextAlignment.Left", "end" => "TextAlignment.Right"
    }
    alignType = css_align_to_modelica[align]
    add_attribute("horizontalAlignment", alignType)
  end
end

parseSVG(ARGV[0])
