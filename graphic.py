import logging

from common import *
from environment import Environment as env
import gbrtypes
import numeric
import command
import aperture

class GraphicObject (Generator, gbrtypes.Polar):

  # Graphic attributes to associate with object.
  object_attributes = gbrtypes.ObjectAttributes

  def __init__(self, polarity):
    gbrtypes.Polar.__init__(self, polarity)

    self.object_attributes = gbrtypes.ObjectAttributes()

  def generate(self, stream):
    self.object_attributes.generate(stream)

  def cleanup(self, stream):
    self.object_attributes.cleanup(stream)

# 2-dimensional line segment with no width. Only used to construct a Region.
class Segment (Generator):

  vectors = (numeric.Vector, numeric.Vector)
  interp_mode = gbrtypes.InterpMode
  quad_mode = gbrtypes.QuadrantMode
  center = numeric.Vector

  def __init__(self, vectors, interp_mode=None, quad_mode=None, center=None):

    vectors = (numeric.Vector(vectors[0]), numeric.Vector(vectors[1]))
    if interp_mode is None: interp_mode = gbrtypes.Linear()
    if quad_mode is None: quad_mode = gbrtypes.Auto()

    self.vectors = vectors
    self.interp_mode = interp_mode
    self.quad_mode = quad_mode
    self.center = center

  def generate(self, stream):

    # set interpolation
    env.engine.set_interp(stream, self.interp_mode, self.center)

    # set quadrant mode
    env.engine.set_quad(stream, self.quad_mode)

    # ensure current vector is at start
    env.engine.move(stream, self.vectors[0])

    # create linear segment
    env.engine.interpolate(stream, self.vectors[1])

# Builds list of segments with region mode on.
class Region (GraphicObject):

  # Aperture attributes to associate with object.
  aperture_attributes = gbrtypes.ApertureAttributes

  # list of Segment objects
  segments = list

  def __init__(self, segments=list(), polarity=None):
    GraphicObject.__init__(self, polarity)

    self.aperture_attributes = gbrtypes.ApertureAttributes()
    self.segments = list()

    # normalize segments to form closed region
    if len(segments) > 0:

      if type(segments[0]) is Segment:

        # append given segments
        self.segments += segments

      else:

        # assemble simple polygon from vectors
        vectors = segments

        # normalize vectors
        vectors = [numeric.Vector(vector) for vector in vectors]

        for idx in range(len(vectors) - 1):
          self.segments.append(Segment((vectors[idx], vectors[idx + 1])))

        # closing segment
        self.segments.append(Segment((vectors[-1], vectors[0])))

  # Map addition/subtraction to Block creation.
  def __add__(self, other): return Block([self, other])

  def __sub__(self, other): return self + other.invert()

  def __str__(self): return 'R%08X' % (id(self))

  def generate(self, stream):
    GraphicObject.generate(self, stream)

    logging.info('Generating region: ' + str(self))

    # reset graphics state
    env.engine.state.reset()

    # comment
    stream.append(command.Comment('Region: ' + str(self)))

    # add aperture attributes
    self.aperture_attributes.generate(stream)

    # ensure current polarity is correct
    env.engine.set_polarity(stream, self.polarity)

    # turn region mode on
    stream.append(command.StartRegion())

    # generate segments
    [segment.generate(stream) for segment in self.segments]

    # generate final D02
    stream.append(command.Move(env.engine.state.vector))

    # turn region mode off
    stream.append(command.EndRegion())

  def cleanup(self, stream):

    self.aperture_attributes.cleanup(stream)

class FlashObject (GraphicObject):

  ap = aperture.Aperture
  vector = numeric.Vector

  def __init__(self, ap, vector, polarity=None):
    GraphicObject.__init__(self, polarity)

    self.ap = ap
    self.vector = vector

  def __str__(self):
    return 'Flash of %s at %s' % (self.ap.d_code, str(self.vector))

  def generate(self, stream):
    GraphicObject.generate(self, stream)

    env.engine.flash(stream, self.ap, self.vector)

# Helper abstraction for a list of regions/flashes with basic 
# arithmetic operations indicating polarity.
class Block (Generator, Appendable):

  object_attributes = gbrtypes.ObjectAttributes
  aperture_attributes = gbrtypes.ApertureAttributes

  objects = list

  # objects by category
  regions = list
  flashes = list

  def __init__(self, objects=list()):

    if not type(objects) is list: objects = [objects]

    self.object_attributes = gbrtypes.ObjectAttributes()
    self.aperture_attributes = gbrtypes.ApertureAttributes()

    self.objects = list()
    self.regions = list()
    self.flashes = list()

    Appendable.__init__(self, [
      (Region, self.regions, self.append_region),
      (FlashObject, self.flashes, self.append_flash),
      (Block, None, self.append_block),
      (gbrtypes.ObjectAttributes, None, self.append_obj_attr),
      (gbrtypes.ApertureAttributes, None, self.append_ap_attr),
    ])

    for obj in objects: self.append(obj)

  def __add__(self, other):
    self.append(other)
    return self

  def __sub__(self, other):
    objs = []
    if not type(other) is list: other = [other]
    for obj in other:
      if issubclass(type(obj), GraphicObject):
        objs.append(obj.invert())
      elif issubclass(type(obj), Block):
        objs += [o.invert() for o in obj.objects]
      else:
        raise Exception('Unsupported operand: ' + type(o).__name__)
    self.append(objs)
    return self

  def __str__(self): return 'B%08X' % (id(self))

  # todo: refactor attribute handling

  def append_region(self, region):
    region.object_attributes = self.object_attributes
    region.aperture_attributes = self.aperture_attributes
    self.objects.append(region)

  def append_flash(self, region):
    region.object_attributes = self.object_attributes
    self.objects.append(region)

  def append_block(self, block):
    self.append(block.regions)
    self.append(block.flashes)

  def append_obj_attr(self, attr):
    self.object_attributes = attr
    [region.append(attr) for region in self.regions]
    [flash.append(attr) for flash in self.flashes]

  def append_ap_attr(self, attr):
    self.aperture_attributes = attr
    for region in self.regions:
      region.aperture_attributes = attr

    for flash in self.flashes:
      region.aperture_attributes = attr

  def generate(self, stream):

    logging.debug('Generating block %s: %d regions, %d flashes' % (
      str(self), len(self.regions), len(self.flashes)))

    for obj in self.objects: obj.generate(stream)
