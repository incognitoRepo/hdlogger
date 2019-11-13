import inspect
from bdb import Bdb

class minimalTracer(Bdb):
  def __init__(self):
    Bdb.__init__(self)
    self.breakpoints = dict()
    self.set_trace()

  def set_breakpoint(self, filename, lineno, method):
    """provide a method to apply to a frame object"""
    self.set_break(filename, lineno)
    try:
      self.breakpoints[(filename, lineno)].add(method)
    except KeyError:
      self.breakpoints[(filename, lineno)] = [method]

  def user_line(self, frame):
    if not self.break_here(frame):
      return

    # Get filename and lineno from frame
    (filename, lineno, _, _, _) = inspect.getframeinfo(frame)

    methods = self.breakpoints[(filename, lineno)]
    for method in methods:
      method(frame)
