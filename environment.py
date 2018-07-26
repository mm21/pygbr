from common import *
import gbrtypes

# GBR-level abstraction to contain top-level state.
# Used as a singleton object.
class Environment:

  cf = gbrtypes.CoordinateFormat
  unit = gbrtypes.Unit

  engine = None

  @classmethod
  def init(cls, cf, unit):

    cls.cf = cf
    cls.unit = unit

    import engine
    cls.engine = engine.Engine()
