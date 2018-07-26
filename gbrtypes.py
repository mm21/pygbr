from common import *
import copy
import logging

# ------------------------------------------------------------------------------
# Basic types.
# ------------------------------------------------------------------------------

class LayerIndex:
  index = int
  def __init__(self, index):
    self.index = index
  def __str__(self):
    return'L%d' % (self.index)

class LayerType:

  PLANE = 'Plane'
  SIGNAL = 'Signal'
  MIXED = 'Mixed'
  HATCHED = 'Hatched'

class Side:

  TOP = 'Top'
  INR = 'Inr'
  BOT = 'Bot'

# For plated drill layers.
class PTHSpan:

  # Top to bottom, plated.
  PTH = 'PTH'

  # Top/bottom to middle.
  BLIND = 'Blind'

  # Middle to middle.
  BURIED = 'Buried'

# For non-plated drill layers.
class NPTHSpan:

  # Top to bottom, non-plated.
  NPTH = 'NPTH'

  # Top/bottom to middle.
  BLIND = 'Blind'

  # Middle to middle.
  BURIED = 'Buried'

class Label:

  DRILL = 'Drill'
  ROUTE = 'Route'
  MIXED = 'Mixed'

# ------------------------------------------------------------------------------
# Specifies how to display coordinate data. Agnostic of actual unit.
# ------------------------------------------------------------------------------
class CoordinateFormat (Renderable):

  # Length of integer part. Must be in range [0, 6].
  int_len = int

  # Length of decimal part. Must be in range [4, 6].
  dec_len = int

  def __init__(self, int_len, dec_len):
    self.int_len = int_len
    self.dec_len = dec_len

  def render(self):
    return '%s%s' % (str(self.int_len), str(self.dec_len))

# ------------------------------------------------------------------------------
# Abstract GBR types:
#   Unit
#   InterpMode
#   QuadrantMode
#   Polarity
#   Mirror
#   Rotation
#   Scale
# ------------------------------------------------------------------------------

class Unit (Renderable, Enum): pass
class Inch (Unit):
  def render(self): return 'IN'
class Millimeter (Unit):
  def render(self): return 'MM'

class InterpMode (Renderable, Enum): pass
class Linear (InterpMode): pass

class Circular (InterpMode): pass

class Clockwise (Circular): pass
class CounterClockwise (Circular): pass

# Only applicable for interpolation mode subclassing Circular.
class QuadrantMode (Renderable, Enum): pass
class Single (QuadrantMode): pass
class Multi (QuadrantMode): pass

# Automatically pick based on angle x, for small value epsilon.
# Note: if start == end, most likely client is drawing a circle or has a bug.
# 0 <= x <= epsilon             Single, no discontinuity around 0 degrees.
# epsilon < x || start == end   Multi, no discontinuity around 90 degrees.
class Auto (QuadrantMode): pass

# Polarity
class Polarity (Renderable, Enum):
  def __mul__(self, other):
    if int(self) * int(other) > 0:
      return Dark()
    else:
      return Clear()
class Dark (Polarity):
  def __int__(self): return 1
  def render(self): return 'D'
  def invert(self): return Clear()
class Clear (Polarity):
  def __int__(self): return -1
  def render(self): return 'C'
  def invert(self): return Dark()

# Rotation
class Rotation (Renderable): pass

# Scale
class Scale (Renderable): pass

# ------------------------------------------------------------------------------
# Represents an object maintaining a concept of polarity.
# ------------------------------------------------------------------------------
class Polar:

  # Polarity object.
  polarity = Polarity

  def __init__(self, polarity=None):
    if polarity is None: polarity = Dark()
    self.polarity = polarity

  # "Shallow" invert: just return new object, inverting this object's polarity
  def invert(self): 
    ret = copy.copy(self)
    ret.polarity = ret.polarity.invert()
    return ret

  # Multiplication by polarity: return new object, polarity toggled by other.
  def __mul__(self, other):
    ret = copy.copy(self)
    ret.polarity *= int(other)
    return self

# ------------------------------------------------------------------------------
#
# Attribute
#   File attributes
#     .Part
#     .FileFunction
#     ...
#   Aperture attributes
#     .AperFunction
#     .DrillTolerance
#     .FlashText
#   Object attributes
#     .N
#     .C
#     .P
#
# ------------------------------------------------------------------------------

class Attribute (Generator):

  # Directly overridden by subclass.
  name = str

  # Instantiated in this class and appended by subclass.
  values = [str]

  def __init__(self, values=None):
    if values is None: values = list()
    self.values = values

  def __str__(self):
    return '%s=%s' % (self.name, ','.join([str(v) for v in self.values]))

  def generate(self, stream):
    import command

    # get cmd based on attribute type
    if issubclass(type(self), FileAttribute):
      cmd = command.AddFileAttribute
    elif issubclass(type(self), ApertureAttribute):
      cmd = command.AddApertureAttribute
    else:
      cmd = command.AddObjectAttribute

    stream.append(cmd('%s,%s' % (self.name,
      ','.join([str(v) for v in self.values]))))

  def cleanup(self, stream):
    import command
    stream.append(command.DeleteAttribute('%s' % (self.name)))

class FileAttribute (Attribute):

  # If set, becomes first element of values in Attribute.
  attr = str

  def __init__(self, values=None):
    if values is None: values = list()
    if not type(values) is list: values = [values]
    if not self.attr is str:
      values = [self.attr] + values
    Attribute.__init__(self, values)

# ------------------------------------------------------------------------------
#
# FileAttribute: .Part
#
# ------------------------------------------------------------------------------

class Part (FileAttribute):
  name = '.Part'

# Single PCB.
class Single (Part):
  attr = 'Single'

# A.k.a. "customer panel"/"assembly panel"/"shipping panel"/"biscuit".
class Array (Part):
  attr = 'Array'

# A.k.a. "working panel"/"production panel".
class FabricationPanel (Part):
  attr = 'FabricationPanel'

# Test coupon.
class Coupon (Part):
  attr = 'Coupon'

# Other part with mandatory description.
class Other (Part):
  attr = 'Other'

  def __init__(self, field):
    FileAttribute.__init__(self, [field])

# ------------------------------------------------------------------------------
#
# FileAttribute: .FileFunction
#
# ------------------------------------------------------------------------------

class FileFunction (FileAttribute):

  name = '.FileFunction'

# ------------------------------------------------------------------------------
# Essential files
# ------------------------------------------------------------------------------

class Copper (FileFunction):

  attr = 'Copper'
  
  def __init__(self, index, side, layertype=None):
    FileFunction.__init__(self)

    index = LayerIndex(index)

    self.values += [index, side]
    if not layertype is None:
      self.values.append(layertype)

class Plated (FileFunction):

  attr = 'Plated'

  def __init__(self, index_from, index_to, pth_span, label=None):
    FileFunction.__init__(self)

    self.values += [LayerIndex(index_from), LayerIndex(index_to), pth_span]
    if not label is None:
      self.values.append(label)

class NonPlated (FileFunction):

  attr = 'NonPlated'

  def __init__(self, index_from, index_to, pth_span, label=None):
    FileFunction.__init__(self)

    self.values += [LayerIndex(index_from), LayerIndex(index_to), pth_span]
    if not label is None:
      self.values.append(label)

class Profile (FileFunction):

  attr = 'Profile'

  class Type:
    Plated = 'P'
    NonPlated = 'NP'

  # todo: plated/non-plated
  def __init__(self, plated=Type.NonPlated):
    FileFunction.__init__(self)

    self.values.append(plated)

class Soldermask (FileFunction):

  attr = 'Soldermask'

  # Index not present if only one soldermask per side.
  def __init__(self, side, index=None):
    FileFunction.__init__(self)
    self.values += [side]
    if not index is None:
      self.values.append(LayerIndex(index))

# Legend / silkscreen.
class Legend (FileFunction):

  attr = 'Legend'

  # Index not present if only one legend per side.
  def __init__(self, side, index=None):
    FileFunction.__init__(self)
    self.values += [side]
    if not index is None:
      self.values.append(LayerIndex(index))

# ------------------------------------------------------------------------------
# Fabrication mask files
# ------------------------------------------------------------------------------

class FabMask (FileFunction):

  # Index not present if only one mask per side.
  def __init__(self, side, index=None):
    FileFunction.__init__(self)
    self.values += [side]
    if not index is None:
      self.values.append(LayerIndex(index))

class Paste (FabMask):
  attr = 'Paste'
class Carbonmask (FabMask):
  attr = 'Carbonmask'
class Gluemask (FabMask):
  attr = 'Gluemask'
class Goldmask (FabMask):
  attr = 'Goldmask'
class Heatsinkmask (FabMask):
  attr = 'Heatsinkmask'
class Peelablemask (FabMask):
  attr = 'Peelablemask'
class Silvermask (FabMask):
  attr = 'Silvermask'
class Tinmask (FabMask):
  attr = 'Tinmask'

# ------------------------------------------------------------------------------
# Drawing files
# ------------------------------------------------------------------------------

# Not implemented.

class ArrayDrawing (FileFunction):
  attr = 'ArrayDrawing'
class AssemblyDrawing (FileFunction):
  attr = 'AssemblyDrawing'
class Drillmap (FileFunction):
  attr = 'Drillmap'
class FabricationDrawing (FileFunction):
  attr = 'FabricationDrawing'
class OtherDrawing (FileFunction):
  attr = 'OtherDrawing'

# ------------------------------------------------------------------------------
# Other files
# Not normally needed in a fabrication data set.
# ------------------------------------------------------------------------------

# Not implemented.

class Keepout (FileFunction):
  attr = 'Keep-out'
class Pads (FileFunction):
  attr = 'Pads'
class Other (FileFunction):
  attr = 'Other'

# ------------------------------------------------------------------------------
#
# FileAttribute: .FilePolarity
#
# ------------------------------------------------------------------------------

class FilePolarity (FileAttribute):
  name = '.FilePolarity'

class Positive (FilePolarity):
  attr = 'Positive'
class Negative (FilePolarity):
  attr = 'Negative'

# ------------------------------------------------------------------------------
#
# FileAttribute: .GenerationSoftware
#
# ------------------------------------------------------------------------------

class GenerationSoftware (FileAttribute):
  name = '.GenerationSoftware'

  def __init__(self, vendor, app, ver):
    Attribute.__init__(self, [vendor, app, ver])

# ------------------------------------------------------------------------------
#
# FileAttribute: .CreationDate
#
# ------------------------------------------------------------------------------

class CreationDate (FileAttribute):
  name = '.CreationDate'

  def __init__(self, datetime):
    Attribute.__init__(self, [datetime])

# ------------------------------------------------------------------------------
#
# FileAttribute: .ProjectId
#
# ------------------------------------------------------------------------------

class ProjectId (FileAttribute):
  name = '.ProjectId'

  # project_id: gbrtypes.String object
  # project_guid: GUID conforming to RFC4122 v1/v4
  # rev_id: gbrtypes.String object
  def __init__(self, project_id, rev_id, project_guid=None):

    if project_guid is None:
      import hashlib
      
      # form GUID based on project_id/rev_id
      project_id_full = project_id + rev_id
      project_hash = hashlib.md5(project_id_full.encode()).hexdigest()
      project_guid = '%s-%s-%s-%s-%s' % (
        project_hash[:8],
        project_hash[8:12],
        project_hash[12:16],
        project_hash[16:20],
        project_hash[20:])

    Attribute.__init__(self, [project_id, project_guid, rev_id])

# ------------------------------------------------------------------------------
#
# FileAttribute: .MD5
#
# ------------------------------------------------------------------------------

# Must be placed immediately before EOF command.
# Calculated from start of file to start of command, not including
# line endings.
class MD5 (FileAttribute):
  name = '.MD5'

  # reference to containing layer
  layer = None

  def __init__(self, layer):
    FileAttribute.__init__(self)
    self.layer = layer

  # get current file contents from env
  def generate(self, stream):

    import hashlib

    # get handle of file being generated
    fh = self.layer.fh

    # go to beginning of file
    fh.seek(0)

    # read out entire contents so far
    contents = ''.join([line.strip() for line in fh.readlines()])

    # write md5 of contents
    md5 = hashlib.md5(contents.encode()).hexdigest()
    self.values.append(md5)

    logging.info('MD5: %s' % (md5))

    FileAttribute.generate(self, stream)

# ------------------------------------------------------------------------------
#
# ApertureAttribute
#
# ------------------------------------------------------------------------------

class ApertureAttribute (Attribute): pass

# ------------------------------------------------------------------------------
#
# ApertureAttribute: ApertureFunction
#
# ------------------------------------------------------------------------------

class ApertureFunction (ApertureAttribute):
  name = '.AperFunction'

  # Becomes first element of values in Attribute.
  func = str

  def __init__(self, values=None):
    if values is None: values = list()
    Attribute.__init__(self, [self.func] + values)

# ------------------------------------------------------------------------------
# ApertureAttribute: ApertureFunction: Drill/route layers
#
# Note: only use in layers with .FileFunction=Plated or NonPlated.
# ------------------------------------------------------------------------------

# Via hole to connect different layers.
class ViaDrill (ApertureFunction):
  func = 'ViaDrill'

  # filled: optional boolean
  def __init__(self, filled=None):
    values = list()
    if not filled is None:
      if filled == True:
        values.append('Filled')
      elif filled == False:
        values.append('NotFilled')
      else:
        raise Exception()

    ApertureFunction.__init__(self, values)

# Hole to remove plating in another hole.
class BackDrill (ApertureFunction):
  func = 'BackDrill'

# Hole for through-hole component leads.
class ComponentDrill (ApertureFunction):
  func = 'ComponentDrill'

  # pressfit: optional boolean to indicate press-fit component leads
  #   note: can only be applied on PTH holes
  def __init__(self, pressfit=False):
    values = list()
    if pressfit:
      values.append('PressFit')

    ApertureFunction.__init__(self, values)

# PCB slots.
class Slot (ApertureFunction):
  func = 'Slot'

# Hole with mechanical function: infrastructure, screw, etc.
class MechanicalDrill (ApertureFunction):
  func = 'MechanicalDrill'

  class Type:

    # Holes to attach board or panel temporarily during assembly/test.
    TOOLING = 'Tooling'

    # Non-plated holes forming break-out tab.
    BREAKOUT = 'BreakOut'

    # Other.
    OTHER = 'Other'

  # drilltype: optional, can take MechanicalDrill.Type
  def __init__(self, drilltype=None):
    values = list()
    if not drilltype is None:
      values.append(drilltype)

# Plated holes cut-through by board edge to join PCBs.
class CastellatedDrill (ApertureFunction):
  func = 'CastellatedDrill'

# PCB cut-outs. Can be present in all PCB layers.
class CutOut (ApertureFunction):
  func = 'CutOut'

# Cavity in a PCB.
class Cavity (ApertureFunction):
  func = 'Cavity'

# Hole with no other applicable function.
class OtherDrill (ApertureFunction):
  func = 'OtherDrill'

  # othertype: mandatory, informal description of type
  def __init__(self, othertype):
    ApertureFunction.__init__(self, [othertype])

# ------------------------------------------------------------------------------
# ApertureAttribute: ApertureFunction: Copper layers
#
# Note: only use in layers with .FileFunction=Copper. Some are applicable only
# to outer layers.
# ------------------------------------------------------------------------------

# Pad specifier.
class PadSpec:

  # Copper pad: free of solder mask, defines area to be covered by
  # solder paste.
  COPPER = 'CuDef'

  # Solder mask defined: solder mask overlaps copper pad, area to be covered
  # by solder paste defined by solder mask opening.
  SOLDERMASK = 'SMDef'

# Pad belonging to footprint of a through-hole component.
# By definition, electrically connected to PCB.
class THComponentPad (ApertureFunction):
  func = 'ComponentPad'

  # pressfit: optional boolean to indicate pad belonging press-fit component
  def __init__(self, pressfit=False):
    values = list()
    if pressfit:
      values.append('PressFit')

    ApertureFunction.__init__(self, values)

# Pad belonging to footprint of an SMD component.
# By definition, electrically connected to PCB.
# Only applicable to outer layers.
class SMDPad (ApertureFunction):
  func = 'SMDPad'

  # padspec: mandatory, PadSpec
  def __init__(self, padspec):
    ApertureFunction.__init__(self, [padspec])

# Pad belonging to footprint of a BGA component.
# By definition, electrically connected to PCB.
# Only applicable to outer layers.
class BGAPad (ApertureFunction):
  func = 'BGAPad'

  # padspec: mandatory, PadSpec
  def __init__(self, padspec):
    ApertureFunction.__init__(self, [padspec])

# Edge connector pad.
# Only applicable to outer layers.
class ConnectorPad (ApertureFunction):
  func = 'ConnectorPad'

# Heat sink or thermal pad, typically for SMDs.
class HeatsinkPad (ApertureFunction):
  func = 'HeatsinkPad'

# Via pad. Provides a ring to attach to plating in the barrel.
# Reserved for pads that have no other function. Other pads such as component
# pads may coincidentally function as vias.
class ViaPad (ApertureFunction):
  func = 'ViaPad'

# Test pad. May also act as a via pad, but for test functionality no
# solder mask is applied.
# Only applicable to outer layers.
class TestPad (ApertureFunction):
  func = 'TestPad'

# Pads on plated holes cut-through by board edge. Used to join PCBs.
class CastellatedPad (ApertureFunction):
  func = 'CastellatedPad'

# Fiducial pad with given scope.
class FiducialPad (ApertureFunction):
  func = 'FiducialPad'

  class Scope:

    # Global scope: entire image/PCB
    GLOBAL = 'Global'

    # Local scope: component
    LOCAL = 'Local'

  # scope: scope to which fiducial applies
  def __init__(self, scope):
    ApertureFunction.__init__(self, [scope])

# Thermal relief pad: connects to surrounding copper while
# restricting heat flow.
class ThermalReliefPad (ApertureFunction):
  func = 'ThermalReliefPad'

# Pad around non-plated hole without electrical function.
# May have several functions, notably mechanically strengthening PCB where
# fixed with a bolt.
class WasherPad (ApertureFunction):
  func = 'WasherPad'

# Pad with clear polarity (set with LPC command) creating a clearance in a
# plane. Allows for a drill pass which does not connect to plane.
# Note LPC command must still be explicitly issued.
class AntiPad (ApertureFunction):
  func = 'AntiPad'

# Other pad where given mandatory field informally describes the type.
class OtherPad (ApertureFunction):
  func = 'OtherPad'

  def __init__(self, field):
    ApertureFunction.__init__(self, [field])

# Copper which electrically connects pads or provides shielding.
# May be tracks or pours such as power/ground planes.
# In particular, copper pours generated by regions should carry this attribute.
class Conductor (ApertureFunction):
  func = 'Conductor'

# Copper which acts as a functional electrical component, e.g. transformers,
# inductors, and capacitors.
class EtchedComponent (ApertureFunction):
  func = 'EtchedComponent'

# Copper which has no electrical function such as text and graphics.
class NonConductor (ApertureFunction):
  func = 'NonConductor'

# Copper pattern added to balance copper coverage for plating process.
class CopperBalancing (ApertureFunction):
  func = 'CopperBalancing'

# Copper border around a production panel.
class Border (ApertureFunction):
  func = 'Border'

# Another copper function with mandatory description.
class OtherCopper (ApertureFunction):
  func = 'OtherCopper'

  def __init__(self, field):
    ApertureFunction.__init__(self, [field])

# ------------------------------------------------------------------------------
# ApertureAttribute: ApertureFunction: All layers
#
# Can be used on all layers, including plated/non-plated (drill) and copper.
# ------------------------------------------------------------------------------

# Outline of PCB. Must be present in a dedicated file.
class AperProfile (ApertureFunction):
  func = 'Profile'

# Objects that do not represent a physical part of the PCB.
# Should not be used in copper layers.
class NonMaterial (ApertureFunction):
  func = 'NonMaterial'

# Identifies material objects in the data file.
# For solder masks, typically represent "negative" material objects.
# For copper/drill layers, this function cannot be used.
class Material (ApertureFunction):
  func = 'Material'

# Other function with mandatory description.
class Other (ApertureFunction):
  func = 'Other'

  def __init__(self, field):
    ApertureFunction.__init__(self, [field])

# ------------------------------------------------------------------------------
#
# ApertureAttribute: DrillTolerance
#
# ------------------------------------------------------------------------------

# Tolerance of drill holes.
class DrillTolerance (ApertureAttribute):
  name = '.DrillTolerance'

# ------------------------------------------------------------------------------
#
# ApertureAttribute: FlashText
#
# ------------------------------------------------------------------------------

# Meaning of a flash representing text.
class FlashText (ApertureAttribute):
  name = '.FlashText'

# ------------------------------------------------------------------------------
#
# ObjectAttribute
#
# ------------------------------------------------------------------------------
class ObjectAttribute (Attribute): pass

# ------------------------------------------------------------------------------
#
# ObjectAttribute: NetName
#
# ------------------------------------------------------------------------------

class NetName (ObjectAttribute):
  name = '.N'

# ------------------------------------------------------------------------------
#
# ObjectAttribute: ComponentName
#
# ------------------------------------------------------------------------------

class ComponentName (ObjectAttribute):
  name = '.C'

# ------------------------------------------------------------------------------
#
# ObjectAttribute: PinName
#
# ------------------------------------------------------------------------------

class PinName (ObjectAttribute):
  name = '.P'

# ------------------------------------------------------------------------------
#
# Attribute containers
#
# ------------------------------------------------------------------------------

# Helper container of attributes.
class Attributes (Generator, Appendable):

  # List of possible attributes as classes provided by subclass.
  attrs = list

  # Populated based on attr_classes.
  attr_keys = list

  # Provided by user.
  attr_objs = dict

  def __init__(self):

    # populate keys
    self.attr_keys = [attr.name for attr in self.attrs]

    # initialize object dict
    self.attr_objs = dict()

  def __getitem__(key):
    return self.attr_objs[key]

  def __setitem__(key, value):
    self.attr_objs[key] = value

  def generate(self, stream):
    for name in self.attr_keys:
      if name in self.attr_objs:
        self.attr_objs[name].generate(stream)

  def cleanup(self, stream):
    for name in self.attr_keys:
      if name in self.attr_objs:
        self.attr_objs[name].cleanup(stream)

  def append(self, attrs):
    attrs = Appendable.normalize(attrs)

    for attr in attrs:

      # ensure this attribute belongs to this container
      if not attr.name in self.attr_keys:
        raise Exception('Unknown attribute %s for container %s' % (
          attr.name, str(self)))

      self.attr_objs[attr.name] = attr

class FileAttributes (Attributes):

  attrs = [
    FileFunction,

    Part,
    FilePolarity,

    GenerationSoftware,
    CreationDate,

    ProjectId,
    MD5
  ]

class ApertureAttributes (Attributes):

  attrs = [
    ApertureFunction,
    DrillTolerance,
    FlashText
  ]

class ObjectAttributes (Attributes):

  attrs = [
    NetName,
    ComponentName,
    PinName
  ]
