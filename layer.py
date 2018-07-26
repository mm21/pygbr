import datetime
import logging

from common import *
from environment import Environment as env
import gbrtypes
import command
import aperture
import graphic

class Layer (Generator, Appendable):

  # attributes
  attributes = gbrtypes.FileAttributes

  # list of apertures defined by user
  apertures = list
  
  # graphics objects
  graphics = list

  # file handle set during generation of output file
  fh = None

  def __init__(self, polarity, project_id):

    self.attributes = gbrtypes.FileAttributes()
    self.apertures = list()
    self.graphics = list()

    Appendable.__init__(self, [
      (gbrtypes.FileAttribute, self.attributes, None),
      (aperture.Aperture, self.apertures, self.append_aperture),
      (Generator, self.graphics, self.append_graphic),
      (Renderable, self.graphics, self.append_graphic)
    ])

    # append common attributes
    self.append(polarity)
    self.append(gbrtypes.GenerationSoftware(SW_VENDOR, SW_APP, SW_VER))
    self.append(gbrtypes.CreationDate(datetime.datetime.now().isoformat()))
    if not project_id is None:
      self.append(project_id)

  def __str__(self):
    return 'L%08X' % (id(self))

  # Callback invoked when aperture object is added.
  def append_aperture(self, ap):

    # subtract 1 to start with 0 since aperture already appended
    ap.assign(aperture.DNN_BASE + len(self.apertures) - 1)
    logging.info('Layer %s: Assigned aperture: %s' % (str(self), str(ap)))

  # Callback invoked when graphic object is added.
  def append_graphic(self, obj):

    # make sure aperture is assigned, if applicable
    if hasattr(obj, 'ap'):
      if not obj.ap.assigned:
        self.append(obj.ap)

    logging.info('Layer %s: Added graphic: %s' % (str(self), str(obj)))

  def generate(self, stream):

    block_count = 0
    region_count = 0
    flash_count = 0
    other_count = 0

    # print info about graphics objects to be generated
    for obj in self.graphics:
      if issubclass(type(obj), graphic.Block):
        block_count += 1
        region_count += len(obj.regions)
      elif issubclass(type(obj), graphic.Region):
        region_count += 1
      elif issubclass(type(obj), graphic.FlashObject):
        flash_count += 1
      else:
        other_count += 1

    gen_count = block_count + region_count + flash_count + other_count

    # generate header info
    stream.append(command.SetCoordinateFormat(env.cf))
    stream.append(command.SetUnit(env.unit))

    # generate attributes
    self.attributes.generate(stream)

    # generate aperture definitions
    for ap in self.apertures:
      ap.generate(stream)
      ap.cleanup(stream)

    # generate graphics objects
    for obj in self.graphics:
      obj.generate(stream)
      obj.cleanup(stream)

    # write footer
    stream.append(gbrtypes.MD5(self))
    stream.append(command.EOF())

    logging.info(
      'Layer %s: Generated %d apertures, %d objects (%d blocks, %d regions, '
        '%d flashes, %d other)' % (
        str(self), len(self.apertures), gen_count, block_count, 
        region_count, flash_count, other_count))

  def write(self, file):

    # create new list
    stream = list()

    # open output file and set reference in current layer
    fh = open(file, 'w+')
    self.fh = fh

    # generate self
    self.generate(stream)

    for cmd in stream:

      # recursively expand into renderable commands and write
      def expand(cmd):

        if issubclass(type(cmd), Renderable):
          fh.write(cmd.render() + '\n')
        elif issubclass(type(cmd), Generator):
          gen_list = list()
          cmd.generate(gen_list)
          [expand(gen) for gen in gen_list]
        else:
          raise Exception('Command not renderable: %s' % (str(cmd)))

      expand(cmd)

    fh.close()
    self.fh = None

    logging.info('Wrote "%s", %d commands' % (file, len(stream)))

class OutlineLayer (Layer):

  def __init__(self, project_id=None):
    Layer.__init__(self, gbrtypes.Positive(), project_id)
    self.append(gbrtypes.Profile())

class CopperLayer (Layer):

  def __init__(self, index, side=gbrtypes.Side.TOP, layertype=None,
    project_id=None):
    Layer.__init__(self, gbrtypes.Positive(), project_id)
    self.append(gbrtypes.Copper(index, side, layertype))

class PlatedDrill (Layer):

  def __init__(self, index_from, index_to, pth_span, label=None, 
    project_id=None):
    Layer.__init__(self, gbrtypes.Positive(), project_id)
    self.append(gbrtypes.Plated(index_from, index_to, pth_span, label))

class NonPlatedDrill (Layer):

  def __init__(self, index_from, index_to, npth_span, label=None, 
    project_id=None):
    Layer.__init__(self, gbrtypes.Positive(), project_id)
    self.append(gbrtypes.NonPlated(index_from, index_to, npth_span, label))

class Soldermask (Layer):

  def __init__(self, side=gbrtypes.Side.TOP, index=None, project_id=None):
    Layer.__init__(self, gbrtypes.Negative(), project_id)
    self.append(gbrtypes.Soldermask(side, index))

class Silkscreen (Layer):

  def __init__(self, side=gbrtypes.Side.TOP, index=None, project_id=None):
    Layer.__init__(self, gbrtypes.Positive(), project_id)
    self.append(gbrtypes.Legend(side, index))
