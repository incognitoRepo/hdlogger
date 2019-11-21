import sys, linecache
from functools import singledispatchmethod
from typing import Callable
from types import FunctionType
from bdb import BdbQuit
from inspect import CO_GENERATOR, CO_COROUTINE, CO_ASYNC_GENERATOR

GENERATOR_AND_COROUTINE_FLAGS = CO_GENERATOR | CO_COROUTINE | CO_ASYNC_GENERATOR # 672

class State:
  SYS_PREFIX_PATHS = set((
    sys.prefix,
    sys.exec_prefix,
    os.path.dirname(os.__file__),
    os.path.dirname(collections.__file__),
))

  def __init__(self, frame, event, arg):
    self.frame = frame
    self.event = event
    self.arg = arg
    initialize()

  def initialize(self):
    self.locals = self.frame.f_locals
    self.globals = self.frame.g_globals
    self.function = self.frame.f_code.co_name
    self.function_object = self.frame.f_code
    self.module = self.frame.f_globals.get('__name__','')
    self.filename = self.frame.f_code.co_filename
    self.lineno = self.frame.f_lineno
    self.code = self.frame.f_code
    self.stdlib = True if self.filename.startswith(SYS_PREFIX_PATHS) else False
    self.source = linecache.getline(self.filename, self.lineno, self.frame.f_globals)


class HiDefTracer:

  def __init__(self):
    pass

  def trace_dispatch(self, frame, event, arg):
    print(f"{frame.f_code.co_flags=}, {frame.f_code.co_flags & GENERATOR_AND_COROUTINE_FLAGS}")
    if arg: print(f"{"\n".join([elm for elm in arg])}")
    # if self.quitting:
      # return # None
    if event == 'line':
      return self.dispatch_line(frame)
    if event == 'call':
      return self.dispatch_call(frame, arg)
    if event == 'return':
      return self.dispatch_return(frame, arg)
    if event == 'exception':
      return self.dispatch_exception(frame, arg)
    if event == 'c_call':
      return self.trace_dispatch
    if event == 'c_exception':
      return self.trace_dispatch
    if event == 'c_return':
      return self.trace_dispatch
    print('bdb.Bdb.dispatch: unknown debugging event:', repr(event))
    return self.trace_dispatch

  def dispatch_call(self, frame, arg):
    self.user_call(frame, arg)
    return self.trace_dispatch

  def dispatch_line(self, frame):
    self.user_line(frame)
    return self.trace_dispatch

  def dispatch_return(self, frame, arg):
    self.user_return(frame, arg)
    return self.trace_dispatch

  def dispatch_exception(self, frame, arg):
    self.user_exception(frame, arg)
    return self.trace_dispatch

  def user_call(self, frame, argument_list):
    print('user_call')
    print(f"{argument_list=}")
    return self.trace_dispatch

  def user_line(self, frame):
    print('user_line')
    return self.trace_dispatch

  def user_return(self, frame, return_value):
    print('user_return')
    print(f"{return_value=}")
    frame.f_locals['__return__'] = return_value

  def user_exception(self, frame, exc_info):
    print('user_exception')
    print(f"{return_value=}")
    return self.trace_dispatch

  def bp_commands(self, frame):
    # self.currentbp is set in bdb in Bdb.break_here if a breakpoint was hit
    if getattr(self, "currentbp", False) and \
               self.currentbp in self.commands:
      currentbp = self.currentbp
      self.currentbp = 0
      lastcmd_back = self.lastcmd
      self.setup(frame, None)
      for line in self.commands[currentbp]:
        self.onecmd(line)
      self.lastcmd = lastcmd_back
      if not self.commands_silent[currentbp]:
        self.print_stack_entry(self.stack[self.curindex])
      if self.commands_doprompt[currentbp]:
        self._cmdloop()
      self.forget()
      return
    return 1





  def globaltrace_lt(self, frame, why, arg):
    if why == 'call':
      code = frame.f_code
      filename = frame.f_globals.get('__file__', None)
      if filename:
        # XXX _modname() doesn't work right for packages, so
        # the ignore support won't work right for packages
        modulename = _modname(filename)
        if modulename is not None:
          ignore_it = self.ignore.names(filename, modulename)
          if not ignore_it:
            if self.trace:
              print((" --- modulename: %s, funcname: %s" % (modulename, code.co_name)))
            return self.localtrace
      else:
        return None

  @singledispatchmethod
  def run(self, cmd, **kwds):
    raise NotImplementedError

  @run.register
  def _(self, cmd:str, **kwds):
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
  def _(self, cmd:FunctionType, **kwds):

    self.reset()
    sys.settrace(self.trace_dispatch)
    res = None
    try:
      res = cmd(**kwds)
    except BdbQuit:
      pass
    finally:
      self.quitting = True
      sys.settrace(None)
    return res

  def reset(self):
    """Set values of attributes as ready to start debugging."""
    import linecache
    linecache.checkcache()
    self.botframe = None
    # self._set_stopinfo(None, None)


def main():
  from tester.helpers import final_selector
  t = HiDefTracer()
  t.run(final_selector)


if __name__ == '__main__':
  main()
