#
# Robot PAU to motor mapping
# Copyright (C) 2014, 2015 Hanson Robotics
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301  USA

import copy
import math
from scipy.interpolate import interp1d

class MapperBase:
  """
  Abstract base class for motor mappings.  Subclasses of MapperBase will
  be used to remap input values in received messages and convert them to
  motor units. Typically (but not always) the motor units are angles,
  measured in radians.

  The methods 'map' and '__init__' must be implemented when writing a
  new subclass.
  """

  def map(self, val):
    raise NotImplementedError

  def __init__(self, args, motor_entry):
    """
    On construction, mapper classes are passed an 'args' object and a
    'motor_entry' object, taken from a yaml file.  The args object will
    correspond to a 'function' property in the 'binding' stanza. The
    'motor_entry' will be the parent of 'binding', and is used mainly
    to reach 'min' and 'max' properties.  Thus, for example:

        foomotor:
           binding:
             function:
                - name: barmapper
                  bararg: 3.14
                  barmore:  2.718
           min: -1.0
           max: 1.0

    Thus, 'args' could be 'bararg', 'barmore', while 'motor_entry' would be
    the entire 'foomotor' stanza.
    """
    pass

# --------------------------------------------------------------

class Composite(MapperBase):
  """
  Composition mapper. This is initialized with an ordered list of
  mappers.  The output value is obtained by applying each of the
  mappers in sequence, one after the other.  The yaml file must
  specify a list of mappings in the function property.  For example:

          function:
            - name: quaternion2euler
              axis: z
            - name: linear
              scale: -2.92
              translate: 0

  would cause the quaternion2euler mapper function to be applied first,
  followed by the linear mapper.
  """
  def map(self, val):
    for mapper_instance in self.mapper_list:
      val = mapper_instance.map(val)
    return val

  def __init__(self, mapper_list):
    self.mapper_list = mapper_list

# --------------------------------------------------------------

class Linear(MapperBase):
  """
  Linear mapper.  This handles yaml entries that appear in one of the
  two forms.  One form uses inhomogenous coordinates, such as:

     function:
       - name: linear
         scale: -2.92
         translate: 0.3

  The other form specifies a min and max range, such as:

      function:
        - name: linear
          min: 0.252
          max: -0.342

  The first form just rescales the value to the indicated slope and
  offset. The second form rescales such that the indicated input min
  and max match the motor min and max.  For instance, in the second
  case, the input could be specified as min and max radians (for an
  angle), which is converted to motor min and max displacement.
  """

  def map(self, val):
    return (val + self.pretranslate) * self.scale + self.posttranslate

  def __init__(self, args, motor_entry):
    if args.has_key('scale') and args.has_key('translate'):
      self.pretranslate = 0
      self.scale = args['scale']
      self.posttranslate = args['translate']

    elif args.has_key('min') and args.has_key('max'):
      # Map the given 'min' and 'max' to the motor's 'min' and 'max'
      self.pretranslate = -args['min']
      self.scale = (motor_entry['max']-motor_entry['min'])/(args['max']-args['min'])
      self.posttranslate = motor_entry['min']

# --------------------------------------------------------------

class WeightedSum(MapperBase):
  """
  This will map min-max range for every term to intermediate min-max range
  (imin-imax) and then sum them up. Then the intermediate 0..1 range will be
  mapped to the motor min-max range.

  Example:

          function:
            - name: weightedsum
              imin: 0.402
              terms:
              - {min: 0, max: 1, imax: 0}
              - {min: 0, max: 0.6, imax: 1}
  """

  @staticmethod
  def _saturated(val, interval):
    return min(max(val, min(interval["min"],interval["max"])), max(interval["min"],interval["max"]))

  def map(self, vals):
    return sum(
      map(
        lambda (val, translate, scale, term):
          (self._saturated(val, term) + translate) * scale,
        zip(vals, self.pretranslations, self.scalefactors, self.termargs)
      )
    ) + self.posttranslate

  def __init__(self, args, motor_entry):
    range_motors = motor_entry["max"] - motor_entry["min"]

    self.posttranslate = args["imin"] * range_motors + motor_entry["min"]
    self.pretranslations = map(
      lambda term: -term["min"],
      args["terms"]
    )
    self.scalefactors = map(
      lambda term:
        (term["imax"]-args["imin"])/(term["max"]-term["min"])*range_motors,
      args["terms"]
    )
    self.termargs = args["terms"]

# --------------------------------------------------------------

class InterpSum(MapperBase):
    """
    This will sum up relative splines from y0 (neutral position), based on additional set of points defined.
    x represents input of the mapping function (blendshapes, angles) and y is relative value of the motor
    in range between min-max [0-1].
    If input is outside defined range the closest value of the range will be added up
    If a single point is defined the linear interpolation will be used and it is similar to WeightedSum function.

    Example:
            function:
              - name: InterpSum
                y0: 0.4
                terms:
                - {x0: 0, points: [[1,0]]}
                - {x0: 0, points: [[0.6,0.2],[0.8, 0.0]]}
                - {x0: 0.5, points: [[0.6,0.6],[0.7, 0.8],[0.9, 1]]}

            Given inputs of t1,t2,t3 this function would return
            y0 + sum(
              interp_linear([0,0.4],[1,0]) (t1) - y0
              interp_quadratic([0,0.4],[0.6,0.2],[0.8, 0.0]) (t2) - y0
              interp_cubic([0.5,0.4],[0.6,0.6],[0.7, 0.8],[0.9, 1]) (t3) - y0
            )
            where result would be converted to angle
    """

    @staticmethod
    def _saturated(val, interval):
        # Returns value if value is within min max of the input, and closest extreme otherwise
        return min(max(val, min(interval["x0"], interval["xmax"])), max(interval["x0"], interval["xmax"]))


    def map(self, vals):
        return (sum(
            map(
                lambda (val, function, term):
                    function(self._saturated(val, term))-self.y0,
                zip(vals, self.functions, self.termargs)
            )
        ) + self.y0) * self.range + self.motor_min


    def __init__(self, args, motor_entry):
        # Keep parameters to translate relative position to angle.
        self.range = motor_entry["max"] - motor_entry["min"]
        self.motor_min = motor_entry["min"]
        # Neutral position
        self.y0 = args['y0']
        # Create interpolation functions:
        self.functions = []
        self.termargs = []
        for term in args["terms"]:
            # Neutral point
            ax = [term['x0']]
            ay = [self.y0]
            # Additional points
            for p in term["points"]:
                ax.append(p[0])
                ay.append(p[1])
            # Use cubic interpolation for more than 3 points
            method = 'cubic'
            if len(ax) < 3:
                method = 'linear'
            elif len(ax) == 3:
                method = 'quadratic'
            term["xmax"] = ax[-1]
            self.functions.append(interp1d(ax,ay, method))
            self.termargs.append(term)

_mapper_classes = {
  "linear": Linear,
  "weightedsum": WeightedSum,
  "interpsum": InterpSum,
}

def build(yamlobj, motor_entry):
  if isinstance(yamlobj, dict):
    return _mapper_classes[yamlobj["name"]](yamlobj, motor_entry)

  elif isinstance(yamlobj, list):
    return Composite(
      [build(func_entry, motor_entry) for func_entry in yamlobj]
    )
