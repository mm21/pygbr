import logging
import os

import common
import gbrtypes
import numeric
import aperture
import graphic
import layer
from environment import Environment as env

PROJECT_NAME = 's_logo_test'
PROJECT_ID = gbrtypes.ProjectId(PROJECT_NAME, '1.0')

COORD_FORMAT = gbrtypes.CoordinateFormat(2, 6)
UNIT = gbrtypes.Inch

BOARD_SIZE_X = 100.000
BOARD_SIZE_Y = 100.000

# min edge spacing
TOL_EDGE = 0.100

# ratio of center circle diameter to width
CIRC_MID_RATIO = 0.25

# ratio of logo trace to width
LOGO_TRACE_RATIO = CIRC_MID_RATIO / 4

# width of logo
LOGO_WIDTH = 0.800

LOGO_HEIGHT = (3 * LOGO_WIDTH) - (2 * LOGO_TRACE_RATIO * LOGO_WIDTH)

LOGO_SPACING = 0.100

# signal trace width
TRACE_WIDTH = 0.010

# clearance for signal traces
TRACE_CLEARANCE = 0.010

# max # of traces
TRACE_MAX = 8

LOGO_COUNT_X = 5
LOGO_COUNT_Y = 1

def rect(center, width, height):

  region = graphic.Region([
    (center[0] - width / 2, center[1] - height / 2),
    (center[0] + width / 2, center[1] - height / 2),
    (center[0] + width / 2, center[1] + height / 2),
    (center[0] - width / 2, center[1] + height / 2),
  ])

  return region

# returns square with given width
def square(center, width):

  return rect(center, width, width)

# returns circle with given radius
def circle(center, radius):

  circ_vector = numeric.Vector(center + numeric.Vector((radius, 0)))
  region = graphic.Region([
    graphic.Segment((circ_vector, circ_vector), gbrtypes.CounterClockwise(),
      center=center),
  ])

  return region

# returns ring with given outer radius and width
def ring(center, radius, width):

  circ_out = circle(center, radius)
  circ_in = circle(center, radius - width)

  return circ_out - circ_in

# returns contour of waypoints
def contour(vectors, width):

  vectors = [numeric.Vector(v) for v in vectors]
  width = numeric.Scalar(width)

  radius = width / 2

  block = graphic.Block()

  # iterate and generate rectangles

  for vector_idx in range(len(vectors) - 1):
    
    v1 = vectors[vector_idx]
    v2 = vectors[vector_idx + 1]

    if v1[0] == v2[0]:
      # vertical
      center = numeric.Vector((v1[0], (v1[1] + v2[1]) / 2))
      trace_len = numeric.Scalar(val=abs(v1[1] - v2[1]))
      block += rect(center, width, trace_len + width)
    elif v1[1] == v2[1]:
      # horizontal
      center = numeric.Vector(((v1[0] + v2[0]) / 2, v1[1]))
      trace_len = numeric.Scalar(val=abs(v1[0] - v2[0]))
      block += rect(center, trace_len + width, width)
    else:
      raise Exception()

  return block

# returns trace of waypoints with width and clearance
def trace(vectors, width, clearance=0.):

  vectors = [numeric.Vector(v) for v in vectors]
  width = numeric.Scalar(width)
  clearance = numeric.Scalar(clearance)

  block = graphic.Block()

  # generate clearance for all traces
  if clearance != 0:
    block -= contour(vectors, width + clearance * 2)

  # generate traces
  block += contour(vectors, width)

  return block

class Socket (graphic.Block):

  WIDTH = 0.150

  PITCH = 0.050

  # width x height of pad
  PADSPEC = (0.050, 0.020)

  # height: calculated based on # pads, width, pitch

  # location of center
  center = numeric.Vector

  pad_count = int

  # tuple of pad x-coordinates
  pad_x = (numeric.Scalar, numeric.Scalar)

  # list of pad y-coordinates
  pad_y = list

  # pad_count: per side
  def __init__(self, center, pad_count, soldermask):
    graphic.Block.__init__(self)

    self.height = pad_count * self.PADSPEC[1] + \
      (pad_count - 1) * (self.PITCH - self.PADSPEC[1])

    self.center = center
    self.pad_count = pad_count

    self.pad_x = (center[0] - self.WIDTH / 2, center[0] + self.WIDTH / 2)
    self.pad_y = list()

    # find y-coords
    offset = self.PADSPEC[1] / 2
    for pad_idx in range(pad_count):
      self.pad_y.append(
        center[1] - self.height/2 + offset + pad_idx * self.PITCH)

    # generate rectangles for pads
    for x in self.pad_x:
      for y in self.pad_y:
        self += rect((x, y), self.PADSPEC[0], self.PADSPEC[1])
        soldermask.append(rect((x, y), self.PADSPEC[0], self.PADSPEC[1]))

  # returns location of connector for given pad
  def pad_connector(self, side, index):
    offset = self.PADSPEC[0]/2
    if side == 0: offset *= -1
    return numeric.Vector((self.pad_x[side] + offset, self.pad_y[index]))

# returns a logo instance around given center with given params
def s_logo(center, width):

  center = numeric.Vector(center)
  width = numeric.Scalar(width)

  radius = width / 2
  trace_width = width * LOGO_TRACE_RATIO

  logo = graphic.Block()

  square_offset = (width / 4, width - trace_width - width / 4)

  ring_top = ring(center + (0, width - trace_width), radius, trace_width)
  ring_top -= square(
    center + square_offset,
    width / 2)

  ring_bot = ring(center - (0, width - trace_width), radius, trace_width)
  ring_bot -= square(
    center - square_offset,
    width / 2)

  ring_mid = ring(center, radius, trace_width)

  dot = circle(center, radius * CIRC_MID_RATIO)

  logo += ring_top
  logo += ring_bot
  logo += ring_mid
  logo += dot

  return logo

class LogoCkt (graphic.Block):

  TRACE_PITCH = TRACE_CLEARANCE * 2

  trace_count = int

  # list of x coordinates for traces
  trace_x = list

  socket_top = Socket
  socket_bot = Socket

  def __init__(self, center, width, pad_count, soldermask):
    graphic.Block.__init__(self)

    self.trace_count = min(pad_count[0], pad_count[1])

    # find x coordinates to be used for vertical bus
    self.trace_x = list()

    offset = (self.trace_count / 2) * self.TRACE_PITCH
    for idx in range(self.trace_count):
      self.trace_x.append(
        center[0] - offset + self.TRACE_PITCH / 2 + idx * self.TRACE_PITCH)

    self.socket_top = Socket(
      center + (0, width - width * LOGO_TRACE_RATIO),
      pad_count[0],
      soldermask)

    self.socket_bot = Socket(
      center - (0, width - width * LOGO_TRACE_RATIO),
      pad_count[1],
      soldermask)

    if self.trace_count == 0:
      return

    # draw traces
    for idx in range(self.trace_count):
      vectors = list()

      idx_inv = self.trace_count - 1 - idx

      conn1 = self.socket_top.pad_connector(1, idx)
      conn2 = self.socket_bot.pad_connector(0, 
        idx + pad_count[1] - self.trace_count)

      # initial connector
      vectors.append(conn1)

      # draw to angle
      v = conn1 + (idx * self.TRACE_PITCH + self.TRACE_PITCH, 0)
      vectors.append(v)

      # draw to top 1/3
      v = numeric.Vector((v[0], center[1] + width/2 - idx * self.TRACE_PITCH))
      vectors.append(v)

      # draw to middle
      v = numeric.Vector((self.trace_x[idx], v[1]))
      vectors.append(v)

      # draw to bot 1/3
      v = numeric.Vector((v[0],
        center[1] - width/2 - idx * self.TRACE_PITCH + \
          (self.trace_count - 1) * self.TRACE_PITCH))
      vectors.append(v)

      # draw to angle
      v = numeric.Vector(
        (conn2[0] - (idx_inv * self.TRACE_PITCH + self.TRACE_PITCH), v[1]))
      vectors.append(v)

      # draw to y-coord of conn2
      v = numeric.Vector((v[0], conn2[1]))
      vectors.append(v)

      # draw to conn2
      vectors.append(conn2)

      self += trace(vectors, TRACE_WIDTH, TRACE_CLEARANCE)

    # draw top ground traces
    for idx in range(pad_count[0]):
      vectors = list()

      conn1 = self.socket_top.pad_connector(0, idx)

      # initial connector
      vectors.append(conn1)

      # draw out
      v = conn1 - (self.TRACE_PITCH, 0)
      vectors.append(v)

      # draw to middle
      v = numeric.Vector((v[0], self.socket_top.center[1]))
      vectors.append(v)

      # draw to logo
      v = numeric.Vector((center[0] - width/2 + width * LOGO_TRACE_RATIO, v[1]))
      vectors.append(v)

      self += trace(vectors, TRACE_WIDTH, 0)

    # draw bottom ground traces
    for idx in range(pad_count[1]):
      vectors = list()

      conn1 = self.socket_bot.pad_connector(1, idx)

      # initial connector
      vectors.append(conn1)

      # draw out
      v = conn1 + (self.TRACE_PITCH, 0)
      vectors.append(v)

      # draw to middle
      v = numeric.Vector((v[0], self.socket_bot.center[1]))
      vectors.append(v)

      # draw to logo
      v = numeric.Vector((center[0] + width/2 - width * LOGO_TRACE_RATIO, v[1]))
      vectors.append(v)

      self += trace(vectors, TRACE_WIDTH, 0)

    self += self.socket_top
    self += self.socket_bot


# returns logo instance with nested circuit
def s_logo_ckt(center, width, pad_count, soldermask):

  center = numeric.Vector(center)
  width = numeric.Scalar(width)
  
  ckt = graphic.Block()

  ckt += s_logo(center, width)
  ckt += LogoCkt(center, width, pad_count, soldermask)

  return ckt


# initialize logging
logging.basicConfig(
  level=logging.ERROR,
  format='%(levelname)-9s | %(message)s')

env.init(COORD_FORMAT, UNIT)

layer1 = layer.CopperLayer(1, project_id=PROJECT_ID)
layer2 = layer.CopperLayer(2, project_id=PROJECT_ID)

soldermask1 = layer.Soldermask(gbrtypes.Side.TOP, 1, project_id=PROJECT_ID)
soldermask2 = layer.Soldermask(gbrtypes.Side.BOT, 2, project_id=PROJECT_ID)

outline = layer.OutlineLayer(project_id=PROJECT_ID)

# draw outline
vectors = list()

v = numeric.Vector((TRACE_WIDTH / 2, TRACE_WIDTH / 2))
vectors.append(v)

v = numeric.Vector((BOARD_SIZE_X - TRACE_WIDTH / 2, v[1]))
vectors.append(v)

v = numeric.Vector((v[0], BOARD_SIZE_Y - TRACE_WIDTH / 2))
vectors.append(v)

v = numeric.Vector((TRACE_WIDTH / 2, v[1]))
vectors.append(v)

v = numeric.Vector((TRACE_WIDTH / 2, TRACE_WIDTH / 2))
vectors.append(v)

t = trace(vectors, TRACE_WIDTH, 0)

# add Profile as ApertureFunction for block
aa = gbrtypes.ApertureAttributes()
aa.append(gbrtypes.AperProfile())
t.append(aa)

outline.append(t)

# compute top-level offset
offset = numeric.Vector(
  ((BOARD_SIZE_X - LOGO_COUNT_X * LOGO_WIDTH) / \
    (LOGO_COUNT_X),
  (BOARD_SIZE_Y - TOL_EDGE * 2 - LOGO_COUNT_Y * LOGO_HEIGHT) / \
    (LOGO_COUNT_Y + 1)))

for x in range(LOGO_COUNT_X):
  for y in range(LOGO_COUNT_Y):

    center1 = (TOL_EDGE + LOGO_WIDTH/2 + x * (LOGO_WIDTH + LOGO_SPACING),
      TOL_EDGE + LOGO_HEIGHT/2 + y * LOGO_HEIGHT)
    center2 = (
      TOL_EDGE + LOGO_WIDTH/2 + (LOGO_COUNT_X - 1 - x) * \
        (LOGO_WIDTH + LOGO_SPACING),
      TOL_EDGE + LOGO_HEIGHT/2 + y * LOGO_HEIGHT)

    if x == 0 and y == 0:
      pad_count = (0, 0)
      pad_count_rev = (0, 0)
    else:
      top_count = x * 2
      bot_count = x * 2 + 2

      top_count = top_count % (TRACE_MAX + 2)
      bot_count = bot_count % (TRACE_MAX + 2)

      if top_count == 0: top_count = TRACE_MAX
      if bot_count == 0: bot_count = TRACE_MAX

      pad_count = (top_count, bot_count)
      pad_count_rev = (bot_count, top_count)

    logo1 = s_logo_ckt(
      offset + center1,
      LOGO_WIDTH, 
      pad_count,
      soldermask1)

    logo2 = s_logo_ckt(
      offset + center2,
      LOGO_WIDTH, 
      pad_count_rev,
      soldermask2)

    layer1.append(logo1)
    layer2.append(logo2)

if not os.path.exists(PROJECT_NAME):
  os.mkdir(PROJECT_NAME)

layer1.write(os.path.join(PROJECT_NAME, '%s.GTL' % (PROJECT_NAME)))
layer2.write(os.path.join(PROJECT_NAME, '%s.GBL' % (PROJECT_NAME)))

soldermask1.write(os.path.join(PROJECT_NAME, '%s.GTS' % (PROJECT_NAME)))
soldermask2.write(os.path.join(PROJECT_NAME, '%s.GBS' % (PROJECT_NAME)))

outline.write(os.path.join(PROJECT_NAME, '%s.GKO' % (PROJECT_NAME)))
