import sys
from functools import singledispatchmethod
from typing import Callable
from types import FunctionType

class HiDefTracer:

  def __init__(self):
    pass

  def trace_dispatch(self, frame, event, arg):
    if self.quitting:
      return # None
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
    """Invoke user function and return trace function for call event.

    If the debugger stops on this function call, invoke
    self.user_call(). Raise BbdQuit if self.quitting is set.
    Return self.trace_dispatch to continue tracing in this scope.
    """
    # XXX 'arg' is no longer used
    if self.botframe is None:
      # First call of dispatch since reset()
      self.botframe = frame.f_back # (CT) Note that this may also be None!
      return self.trace_dispatch
    if not (self.stop_here(frame) or self.break_anywhere(frame)):
      # No need to trace this function
      return # None
    # Ignore call events in generator except when stepping.
    if self.stopframe and frame.f_code.co_flags & GENERATOR_AND_COROUTINE_FLAGS:
      return self.trace_dispatch
    self.user_call(frame, arg)
    if self.quitting: raise BdbQuit
    return self.trace_dispatch

  def dispatch_line(self, frame):
    """Invoke user function and return trace function for line event.

    If the debugger stops on the current line, invoke
    self.user_line(). Raise BdbQuit if self.quitting is set.
    Return self.trace_dispatch to continue tracing in this scope.
    """
    if self.stop_here(frame) or self.break_here(frame):
      self.user_line(frame)
      if self.quitting: raise BdbQuit
    return self.trace_dispatch

  def dispatch_return(self, frame, arg):
    """Invoke user function and return trace function for return event.

    If the debugger stops on this function return, invoke
    self.user_return(). Raise BdbQuit if self.quitting is set.
    Return self.trace_dispatch to continue tracing in this scope.
    """
    if self.stop_here(frame) or frame == self.returnframe:
      # Ignore return events in generator except when stepping.
      if self.stopframe and frame.f_code.co_flags & GENERATOR_AND_COROUTINE_FLAGS:
        return self.trace_dispatch
      try:
        self.frame_returning = frame
        self.user_return(frame, arg)
      finally:
        self.frame_returning = None
      if self.quitting: raise BdbQuit
      # The user issued a 'next' or 'until' command.
      if self.stopframe is frame and self.stoplineno != -1:
        self._set_stopinfo(None, None)
    return self.trace_dispatch

  def dispatch_exception(self, frame, arg):
    """Invoke user function and return trace function for exception event.

    If the debugger stops on this exception, invoke
    self.user_exception(). Raise BdbQuit if self.quitting is set.
    Return self.trace_dispatch to continue tracing in this scope.
    """
    if self.stop_here(frame):
      # When stepping with next/until/return in a generator frame, skip
      # the internal StopIteration exception (with no traceback)
      # triggered by a subiterator run with the 'yield from' statement.
      if not (frame.f_code.co_flags & GENERATOR_AND_COROUTINE_FLAGS
          and arg[0] is StopIteration and arg[2] is None):
        self.user_exception(frame, arg)
        if self.quitting: raise BdbQuit
    # Stop at the StopIteration or GeneratorExit exception when the user
    # has set stopframe in a generator by issuing a return command, or a
    # next/until command at the last statement in the generator before the
    # exception.
    elif (self.stopframe and frame is not self.stopframe
        and self.stopframe.f_code.co_flags & GENERATOR_AND_COROUTINE_FLAGS
        and arg[0] in (StopIteration, GeneratorExit)):
      self.user_exception(frame, arg)
      if self.quitting: raise BdbQuit

    return self.trace_dispatch

  def user_call(self, frame, argument_list):
    """This method is called when there is the remote possibility
    that we ever need to stop in this function."""
    print(__name__)
    if self._wait_for_mainpyfile:
      return
    if self.stop_here(frame):
      self.message('--Call--')
      self.interaction(frame, None)

  def user_line(self, frame):
    """This function is called when we stop or break at this line."""
    print(__name__)
    if self._wait_for_mainpyfile:
      if (self.mainpyfile != self.canonic(frame.f_code.co_filename)
        or frame.f_lineno <= 0):
        return
      self._wait_for_mainpyfile = False
    if self.bp_commands(frame):
      self.interaction(frame, None)

  def bp_commands(self, frame):
    """Call every command that was set for the current active breakpoint
    (if there is one).

    Returns True if the normal interaction function must be called,
    False otherwise."""
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

  def user_return(self, frame, return_value):
    """This function is called when a return trap is set here."""
    print(__name__)
    if self._wait_for_mainpyfile:
      return
    frame.f_locals['__return__'] = return_value
    self.message('--Return--')
    self.interaction(frame, None)

  def user_exception(self, frame, exc_info):
    """This function is called if an exception occurs,
    but only if we are to stop at or just below this level."""
    print(__name__)
    if self._wait_for_mainpyfile:
      return
    exc_type, exc_value, exc_traceback = exc_info
    frame.f_locals['__exception__'] = exc_type, exc_value

    # An 'Internal StopIteration' exception is an exception debug event
    # issued by the interpreter when handling a subgenerator run with
    # 'yield from' or a generator controlled by a for loop. No exception has
    # actually occurred in this case. The debugger uses this debug event to
    # stop when the debuggee is returning from such generators.
    prefix = 'Internal ' if (not exc_traceback
                  and exc_type is StopIteration) else ''
    self.message('%s%s' % (prefix,
      traceback.format_exception_only(exc_type, exc_value)[-1].strip()))
    self.interaction(frame, exc_traceback)


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
              print((" --- modulename: %s, funcname: %s"
                                   % (modulename, code.co_name)))
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
      res = cmd(*args, **kwds)
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
