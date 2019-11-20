from functools import singledispatchmethod
from typing import Callable
from types import FunctionType

class HiDefTracer:

  def __init__(self):
    pass

  @singledispatchmethod
  def run(self, cmd, **kwds):
    raise NotImplementedError

  @run.register
  def _(self, cmd:str, globals=None, locals=None):
    globals, locals = kwds.get('globals',None), kwds.get('locals',None)
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
  def _(self, cmd:FunctionType, *args, **kwds):
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



def main():
  from tester.helpers import final_selector
  t = HiDefTracer()
  t.run(final_selector)


if name == '__main__':
  main()
