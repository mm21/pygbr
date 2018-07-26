import logging

from common import *
import gbrtypes
import numeric
import command
import aperture

# Internal state.
class State:

  # Current position.
  vector = numeric.Vector

  # Offset given as center in absolute coordinates, for Circular interpolation.
  center = numeric.Vector

  # Interpolation state.
  interp_mode = gbrtypes.InterpMode
  quad_mode = gbrtypes.QuadrantMode

  # Graphics state.
  polarity = gbrtypes.Polarity
  rotation = gbrtypes.Rotation

  current_aperture = aperture.Aperture

  def __init__(self):
    self.reset()

  def reset(self):

    self.vector = None
    self.center = None

    self.quad_mode = None
    self.interp_mode = None
    
    self.polarity = None
    self.rotation = None

    self.current_aperture = None

# Manages internal state. All helper functions must be called at in generate().
class Engine:

  # graphics state
  state = State

  def __init__(self):

    self.state = State()

  def move(self, stream, vector):
    vector = numeric.Vector(vector)

    # if not already at vector, generate Move command
    if not self.state.vector == vector:
      stream.append(command.Move(vector))
      self.state.vector = vector

  def interpolate(self, stream, vector):
    vector = numeric.Vector(vector)

    # get offset, if applicable
    if issubclass(type(self.state.interp_mode), gbrtypes.Circular):

      # create vector of signed diff
      offset = numeric.Vector((
        self.state.center.val[0] - self.state.vector.val[0],
        self.state.center.val[1] - self.state.vector.val[1]))

      # check if offsets are unsigned
      if self.state.quad_mode == gbrtypes.Single: offset = abs(offset)

    else:
      offset = None

    # generate Interpolate command
    stream.append(command.Interpolate(vector, offset))

    # update current vector
    self.state.vector = vector

  def flash(self, stream, ap, vector):

    vector = numeric.Vector(vector)

    if not self.state.current_aperture == ap:

      # set aperture
      stream.append(command.SetAperture(ap))
      self.state.current_aperture = ap

    stream.append(command.Flash(vector))

  def set_interp(self, stream, interp_mode, center=None):

    # note: center only valid for Circular interp mode
    if not center is None:
      self.state.center = numeric.Vector(center)

    if not self.state.interp_mode == interp_mode:

      logging.debug('Setting interpolation: ' + str(interp_mode))

      if interp_mode == gbrtypes.Linear:
        stream.append(command.SetInterpLinear())
      elif interp_mode == gbrtypes.Clockwise:
        stream.append(command.SetInterpClockwise())
      elif interp_mode == gbrtypes.CounterClockwise:
        stream.append(command.SetInterpCounterClockwise())
      else:
        raise Exception('Invalid interpolation mode: ' + str(interp_mode))

      self.state.interp_mode = interp_mode

  def set_polarity(self, stream, polarity):
    if type(polarity) is type: polarity = polarity()

    if not self.state.polarity == polarity:

      logging.debug('Setting polarity: ' + str(polarity))

      stream.append(command.LoadPolarity(polarity))

      self.state.polarity = polarity
  
  def set_quad(self, stream, quad_mode):
    if type(quad_mode) is type: quad_mode = quad_mode()

    if not quad_mode is None:

      # handle auto quad mode
      if quad_mode == gbrtypes.Auto:

        if issubclass(type(self.state.interp_mode), gbrtypes.Circular):
          # todo: use Single for small arcs
          quad_mode = gbrtypes.Multi()
        else:
          # Linear, quad_mode is N/A
          quad_mode = None

      if not self.state.quad_mode == quad_mode:

        logging.debug('Setting quadrant mode: ' + str(quad_mode))

        if quad_mode == gbrtypes.Single:
          stream.append(command.SetQuadSingle())
        elif quad_mode == gbrtypes.Multi:
          stream.append(command.SetQuadMulti())
        else:
          raise Exception()

        self.state.quad_mode = quad_mode
