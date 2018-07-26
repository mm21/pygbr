import logging

from common import *
import gbrtypes
import numeric
import command

# 'nn' from which to start assigning Dnn codes
DNN_BASE = 3000

class Aperture (Generator, Renderable, Appendable, gbrtypes.Polar):

  # 'Dnn'
  d_code = str

  # nn
  index = int

  # attributes
  attributes = gbrtypes.ApertureAttributes

  def __init__(self):

    # init attributes
    self.attributes = gbrtypes.ApertureAttributes()

    gbrtypes.Polar.__init__(self)
    Appendable.__init__(self, [(gbrtypes.Attribute, self.attributes, None)])

    # d_code/index will be assigned later

  def __eq__(self, other):
    if other is None:
      return False
    else:
      return self.d_code == other.d_code

  def __str__(self):
    if self.assigned:
      return self.d_code
    else:
      return 'D[unassigned]'

  def generate(self, stream):

    # add attributes using appropriate command
    self.attributes.generate(stream)

  def cleanup(self, stream):

    # delete attributes
    self.attributes.cleanup(stream)

  def render(self): return self.d_code

  # Called when aperture is added to a layer.
  def assign(self, index):
    self.d_code = 'D%d'% (index)
    self.index = index

  @property
  def assigned(self):
    if type(self.d_code) is type:
      return False
    else:
      return True

class StandardAperture (Aperture):

  template = str

  # List of floats used to specify shape of aperture as necessary.
  params = list

  hole = float

  precision = 6

  def __init__(self, hole=None):
    Aperture.__init__(self)

    if not hole is None: hole = float(hole)

    self.params = list()
    self.hole = hole

  def generate(self, stream):

    Aperture.generate(self, stream)

    params = list(self.params)
    if not self.hole is None: params.append(self.hole)
    params = 'X'.join(
      [str(round(param, self.precision)) for param in params])

    stream.append(command.DefineAperture(self.d_code, self.template, params))

class Circle (StandardAperture):

  template = 'C'

  def __init__(self, diameter, hole=None):
    StandardAperture.__init__(self, hole)
    self.params += [float(diameter)]

  def __str__(self):
    return StandardAperture.__str__(self) + ' (Circle, dia=%s, hole=%s)' % (
      str(self.params[0]), str(self.hole))
    
class Rectangle (StandardAperture):

  template = 'R'

  def __init__(self, x_size, y_size, hole=None):
    StandardAperture.__init__(self, hole)
    self.params += [float(x_size), float(y_size)]

class Obround (StandardAperture):

  template = 'O'

  def __init__(self, x_size, y_size, hole=None):
    StandardAperture.__init__(self, hole)
    self.params += [float(x_size), float(y_size)]

class Polygon (StandardAperture):

  template = 'P'

  def __init__(self, diameter, vertices, rotation=0., hole=None):
    StandardAperture.__init__(self, hole)
    self.params += [float(diameter), int(vertices), float(rotation)]

  def __str__(self):
    return StandardAperture.__str__(self) + \
      ' (Polygon, dia=%s, vertices=%s, rotation=%s, hole=%s)' % (
        str(self.params[0]),
        str(self.params[1]),
        str(self.params[2]),
        str(self.hole))

class Triangle (Polygon):

  def __init__(self, diameter, rotation=0., hole=None):
    Polygon.__init__(self, diameter, 3, rotation, hole)

class Square (Polygon):

  def __init__(self, diameter, rotation=0., hole=None):
    Polygon.__init__(self, diameter, 4, rotation, hole)

class Pentagon (Polygon):

  def __init__(self, diameter, rotation=0., hole=None):
    Polygon.__init__(self, diameter, 5, rotation, hole)

class Hexagon (Polygon):

  def __init__(self, diameter, rotation=0., hole=None):
    Polygon.__init__(self, diameter, 6, rotation, hole)

# Only supported in spec <2016.12>.
# As of this writing there are no capable readers.
class BlockAperture (Aperture):

  block = None

  def __init__(self, block, polarity=None):
    Aperture.__init__(self, polarity)
    self.block = block

  def generate(self, stream):
    Aperture.generate(stream)

    stream.append(command.Comment('Adding block aperture: ' + str(self)))

    stream.append(command.DefineBlockStart(self.d_code))
    self.block.generate(stream)
    stream.append(command.DefineBlockEnd())

# Macros and associated template dictionary not supported.
class Macro (Aperture): pass
class TemplateDict (Generator): pass
