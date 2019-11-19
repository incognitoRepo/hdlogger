from functools import singledispatchmethod
from typing import Callable

class HiDefTracer:

  def __init__(self):
    pass

  @singledispatchmethod
  def run(self, cmd, globals=None, locals=None):
    raise NotImplementedError

  @run.register
  def _(self, cmd:str, globals=None, locals=None):
    if globals is None:
      import __main__
      globals = __main__.__dict__
    if locals is None:
      locals = globals
    self.reset()
    if isinstance(cmd, str):
      cmd = compile(cmd, "<string>", "exec")
    sys.settrace(self.trace_dispatch)
    try:
      exec(obj:=compile(cmd, "<string>", "exec"), globals, locals) # no return value
      return eval(expr:=compile(cmd, "<string>", "eval"), globals, locals) # returns single expression
    except BdbQuit:
      pass
    finally:
      self.quitting = True
      sys.settrace(None)

  @run.register
  def runcall(self, cmd:Callable, *args, **kwds):
    if len(args) >= 2:
      self, func, *args = args
    elif not args:
      raise TypeError("descriptor 'runcall' of 'Bdb' object needs an argument")
    elif 'func' in kwds:
      func = kwds.pop('func')
      self, *args = args
      import warnings
      warnings.warn("Passing 'func' as keyword argument is deprecated", DeprecationWarning, stacklevel=2)
    else:
      raise TypeError('runcall expected at least 1 positional argument, got %d' % (len(args)-1))

    self.reset()
    sys.settrace(self.trace_dispatch)
    res = None
    try:
      res = func(*args, **kwds)
    except BdbQuit:
      pass
    finally:
      self.quitting = True
      sys.settrace(None)
    return res
  runcall.__text_signature__ = '($self, func, /, *args, **kwds)'

