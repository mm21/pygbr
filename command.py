from common import *
import gbrtypes
import numeric

class Command (Renderable):
  opcode = str
  data = list

  def __init__(self, data=None):

    if data is None:
      data = list()
    elif not type(data) is list:
      data = [data]

    # opcode is mandatory, data is optional
    self.data = data

# Identified by code letter G, D, or M followed by code number.
# Preceded by data if applicable.
class FunctionCodeCommand (Command):

  def render(self):
    return ''.join([self.opcode] + self.data) + '*'

# D01, D02, D03
class OperationCodeCommand (FunctionCodeCommand):

  vector = numeric.Vector
  offset = numeric.Vector

  def __init__(self, vector, offset=None):
    FunctionCodeCommand.__init__(self)

    self.vector = vector
    self.offset = offset

  def render(self):

    offset = ''
    if not self.offset is None:
      offset = self.offset.render(('I', 'J'))
    return '%s%s%s*' % (self.vector.render(), offset, self.opcode)

class Interpolate (OperationCodeCommand):
  opcode = 'D01'

class Move (OperationCodeCommand):
  opcode = 'D02'

class Flash (OperationCodeCommand):
  opcode = 'D03'

class SetAperture (FunctionCodeCommand):

  # Dnn, nn >= 10
  opcode = None

  # Aperture object.
  ap = None

  def __init__(self, ap):
    FunctionCodeCommand.__init__(self)

    self.ap = ap

  def render(self):
    self.opcode = self.ap.render()
    return FunctionCodeCommand.render(self)

class SetInterpLinear (FunctionCodeCommand):
  opcode = 'G01'
class SetInterpClockwise (FunctionCodeCommand):
  opcode = 'G02'
class SetInterpCounterClockwise (FunctionCodeCommand):
  opcode = 'G03'

class Comment (FunctionCodeCommand):
  opcode = 'G04'
  text = None
  def __init__(self, text):
    FunctionCodeCommand.__init__(self)
    self.text = text
    self.data.append(' ' + text)

class StartRegion (FunctionCodeCommand):
  opcode = 'G36'
class EndRegion (FunctionCodeCommand):
  opcode = 'G37'

class SetQuadSingle (FunctionCodeCommand):
  opcode = 'G74'
class SetQuadMulti (FunctionCodeCommand):
  opcode = 'G75'

class EOF (FunctionCodeCommand):
  opcode = 'M02'

# Identified by two-character command code followed by data, enclosed by '%'.
# Data blocks are delimited by '*'.
class ExtendedCodeCommand (Command):

  def render(self):
    return '%%%s%%' % (self.opcode + '*'.join(self.data) + '*')

# Sets unit in order to interpret coordinate dta.
class SetUnit (ExtendedCodeCommand):
  opcode = 'MO'
  unit = gbrtypes.Unit
  def __init__(self, unit):
    ExtendedCodeCommand.__init__(self)
    self.unit = unit
    self.data.append(unit().render())

# Mandatory, suggested as first non-comment command.
class SetCoordinateFormat (ExtendedCodeCommand):
  opcode = 'FSLA'
  cf = gbrtypes.CoordinateFormat
  def __init__(self, cf):
    ExtendedCodeCommand.__init__(self)
    self.cf = cf
    self.data.append('X%sY%s' % (cf.render(), cf.render()))

class DefineAperture (ExtendedCodeCommand):
  opcode = 'AD'

  def __init__(self, d_code, template, params):
    ExtendedCodeCommand.__init__(self)
    self.data.append('%s%s,%s' % (d_code, template, params))

class DefineMacroAperture (ExtendedCodeCommand):
  opcode = 'AM'

class DefineBlockStart (ExtendedCodeCommand):
  opcode = 'AB'

  # D-code: Dnn
  d_code = str

  def __init__(self, d_code):
    ExtendedCodeCommand.__init__(self)
    self.d_code = d_code
    self.data.append(d_code)

class DefineBlockEnd (ExtendedCodeCommand):
  opcode = 'AB'

class LoadPolarity (ExtendedCodeCommand):
  opcode = 'LP'

  def __init__(self, polarity):
    ExtendedCodeCommand.__init__(self)
    self.data.append(polarity.render())

class LoadMirror (ExtendedCodeCommand):
  opcode = 'LM'

class LoadRotation (ExtendedCodeCommand):
  opcode = 'LR'

class LoadScale (ExtendedCodeCommand):
  opcode = 'LS'

class StepRepeat (ExtendedCodeCommand):
  opcode = 'SR'

class AddFileAttribute (ExtendedCodeCommand):
  opcode = 'TF'

class AddApertureAttribute (ExtendedCodeCommand):
  opcode = 'TA'

class AddObjectAttribute (ExtendedCodeCommand):
  opcode = 'TO'

class DeleteAttribute (ExtendedCodeCommand):
  opcode = 'TD'
