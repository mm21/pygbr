# ------------------------------------------------------------------------------
# Text definitions.
# ------------------------------------------------------------------------------

SW_VENDOR = 'Soluna Systems'
SW_APP = 'SEDA'
SW_VER = '1.0'

# ------------------------------------------------------------------------------
# Represents an object intended to be translated to GBR-readable code.
# ------------------------------------------------------------------------------
class Renderable:

  # Returns GBR representation of object.
  def render(self): pass

# ------------------------------------------------------------------------------
# Generates commands to be inserted into the command stream.
# ------------------------------------------------------------------------------
class Generator:

  # Inserts Command or other Generator objects into given stream.
  def generate(self, stream): pass

  # Insert any necessary commands to reset the state (e.g. delete attributes).
  def cleanup(self, stream): pass

# ------------------------------------------------------------------------------
# Defines an interface to insert arbitrary objects.
# ------------------------------------------------------------------------------
class Appendable:

  # Maps classes to internal appendable objects.
  # todo: list of tuples: (class, obj_list, cb)
  obj_map = list

  def __init__(self, obj_map):
    self.obj_map = obj_map

  # Append given object to appropriate internal data structure.
  # If not given as list, will be converted to list before processing.
  def append(self, objs):
    objs = Appendable.normalize(objs)

    for obj in objs:
      found = False

      for cls, obj_list, cb in self.obj_map:
        if issubclass(type(obj), cls):

          # append to list
          if not obj_list is None:
            obj_list.append(obj)

          # invoke callback
          if not cb is None:
            cb(obj)

          found = True
          break

      if not found:
        raise Exception('Unsupported object: ' + type(obj).__name__)

  @classmethod
  def normalize(cls, objs):
    if not type(objs) is list:
      objs = [objs]
    return objs

# ------------------------------------------------------------------------------
# Represents an object used as an enum.
# ------------------------------------------------------------------------------
class Enum:

  # Used for comparison, e.g. polarity == Dark, polarity1 == polarity2, etc.
  def __eq__(self, other):
    if type(other) is type:
      return type(self) is other
    else:
      return type(self) is type(other)

  def __str__(self): return type(self).__name__
