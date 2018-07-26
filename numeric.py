from common import *
from environment import Environment as env

# ------------------------------------------------------------------------------
# Basic numeric type formatted with CoordinateFormat.
# ------------------------------------------------------------------------------
class Scalar (Renderable):

  # Canonical value as signed int, with decimal shifted appropriately.
  val = int

  def __init__(self, init=0., val=None):

    if issubclass(type(init), Scalar):
      self.val = init.val
    else:
      if not val is None:
        # val given explicitly
        self.val = int(val)
      else:
        if type(init) is int or type(init) is float:
          init = float(init)
        else:
          raise Exception('Invalid init type for Scalar: %s' % (type(init)))

        # scale by decimal precision to get int value
        self.val = int(round(init * (10 ** env.cf.dec_len)))

  # Mathematical operations.
  def __abs__(self):
    return abs(self.val)
  def __eq__(self, other):
    other = Scalar(other)
    return self.val == other.val
  def __add__(self, other):
    other = Scalar(other)
    return Scalar(val=self.val + other.val)
  def __sub__(self, other):
    other = Scalar(other)
    return Scalar(val=self.val - other.val)
  def __mul__(self, other):
    other = float(other)
    return Scalar(val=self.val * other)
  def __truediv__(self, other):
    other = float(other)
    return Scalar(val=self.val / other)

  def __str__(self):
    return self.render() + ' at 0x%08X' % (id(self))

  # Gives sign of this number, either +1 or -1 as an int.
  @property
  def sign(self): return int((self.val >= 0) - (self.val < 0))

  # Render coordinate in specified coordinate format. 
  # Agnostic of what it represents (X/Y/...)
  def render(self):

    if not type(self.val) is int: raise Exception()

    sign_str = ''
    if self.sign < 0: sign_str = '-'

    return '%s%s' % (sign_str, 
      str(abs(self.val)).rjust(env.cf.int_len + env.cf.dec_len, '0'))

# ------------------------------------------------------------------------------
# Basic 2d type formatted with CoordinateFormat.
# Generates coordinates formatted by FS command.
# ------------------------------------------------------------------------------
class Vector (Renderable):

  # Value as tuple of Scalars.
  val = (Scalar, Scalar)

  def __init__(self, val=(0., 0.)):
    if type(val) is Vector:
      self.val = val.val
    elif type(val) is tuple:
      if type(val[0]) is Scalar or type(val[0]) is int or type(val[0]) is float:
        self.val = (Scalar(val[0]), Scalar(val[1]))
      else:
        raise Exception(str(type(val[0])))
    else:
      raise Exception()

  def __eq__(self, other):
    if other is None:
      return False
    else:
      return self.val[0] == other.val[0] and self.val[1] == other.val[1]

  def __add__(self, other):
    if type(other) is Scalar:
      return Vector((self.val[0] + other.val, self.val[1] + other.val))
    elif type(other) is tuple:
      return Vector((self.val[0] + other[0], self.val[1] + other[1]))
    else:
      return Vector((self.val[0] + other.val[0], self.val[1] + other.val[1]))

  def __sub__(self, other):
    if type(other) is Scalar:
      return Vector((self.val[0] - other.val, self.val[1] - other.val))
    elif type(other) is tuple:
      return Vector((self.val[0] - other[0], self.val[1] - other[1]))
    else:
      return Vector((self.val[0] - other.val[0], self.val[1] - other.val[1]))

  def __abs__(self):
    return Vector((abs(self.val[0]), abs(self.val[1])))

  def __str__(self):
    return self.render() + ' at 0x%08X' % (id(self))

  def __getitem__(self, key):
    return self.val[key]

  # Render vector with given prefix per axis to denote meaning (X/Y, I/J).
  def render(self, prefix=('X', 'Y')):

    out = '%s%s%s%s' % (
      prefix[0], self.val[0].render(), 
      prefix[1], self.val[1].render())

    return out
