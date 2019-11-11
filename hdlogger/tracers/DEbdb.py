"""Debugger basics"""

import fnmatch
import sys
import os
from inspect import CO_GENERATOR, CO_COROUTINE, CO_ASYNC_GENERATOR

__all__ = ["BdbQuit", "Bdb", "Breakpoint"]

GENERATOR_AND_COROUTINE_FLAGS = CO_GENERATOR | CO_COROUTINE | CO_ASYNC_GENERATOR

class BdbQuit(Exception):
  """Exception to give up completely."""

class Bdb:

  def __init__(self, skip=None):
    self.skip = set(skip) if skip else None
    self.breaks = {}
    self.fncache = {}
    self.frame_returning = None

  def canonic(self, filename):
    if filename == "<" + filename[1:-1] + ">":
      return filename
    canonic = self.fncache.get(filename)
    if not canonic:
      canonic = os.path.abspath(filename)
      canonic = os.path.normcase(canonic)
      self.fncache[filename] = canonic
    return canonic

  def reset(self):
    """Set values of attributes as ready to start debugging."""
    import linecache
    linecache.checkcache()
    self.botframe = None
    self._set_stopinfo(None, None)

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

  def is_skipped_module(self, module_name):
    "Return True if module_name matches any skip pattern."
    if module_name is None:  # some modules do not have names
      return False
    for pattern in self.skip:
      if fnmatch.fnmatch(module_name, pattern):
        return True
    return False

  def stop_here(self, frame):
    "Return True if frame is below the starting frame in the stack."
    # (CT) stopframe may now also be None, see dispatch_call.
    # (CT) the former test for None is therefore removed from here.
    if self.skip and \
               self.is_skipped_module(frame.f_globals.get('__name__')):
      return False
    if frame is self.stopframe:
      if self.stoplineno == -1:
        return False
      return frame.f_lineno >= self.stoplineno
    if not self.stopframe:
      return True
    return False

  def break_here(self, frame):
    """Return True if there is an effective breakpoint for this line.

    Check for line or function breakpoint and if in effect.
    Delete temporary breakpoints if effective() says to.
    """
    filename = self.canonic(frame.f_code.co_filename)
    if filename not in self.breaks:
      return False
    lineno = frame.f_lineno
    if lineno not in self.breaks[filename]:
      # The line itself has no breakpoint, but maybe the line is the
      # first line of a function with breakpoint set by function name.
      lineno = frame.f_code.co_firstlineno
      if lineno not in self.breaks[filename]:
        return False

    # flag says ok to delete temp. bp
    (bp, flag) = effective(filename, lineno, frame)
    if bp:
      self.currentbp = bp.number
      if (flag and bp.temporary):
        self.do_clear(str(bp.number))
      return True
    else:
      return False

  def do_clear(self, arg):
    """Remove temporary breakpoint.

    Must implement in derived classes or get NotImplementedError.
    """
    raise NotImplementedError("subclass of bdb must implement do_clear()")

  def break_anywhere(self, frame):
    """Return True if there is any breakpoint for frame's filename.
    """
    return self.canonic(frame.f_code.co_filename) in self.breaks

  # Derived classes should override the user_* methods
  # to gain control.

  def user_call(self, frame, argument_list):
    """Called if we might stop in a function."""
    pass

  def user_line(self, frame):
    """Called when we stop or break at a line."""
    pass

  def user_return(self, frame, return_value):
    """Called when a return trap is set here."""
    pass

  def user_exception(self, frame, exc_info):
    """Called when we stop on an exception."""
    pass

  def _set_stopinfo(self, stopframe, returnframe, stoplineno=0):
    """Set the attributes for stopping.

    If stoplineno is greater than or equal to 0, then stop at line
    greater than or equal to the stopline.  If stoplineno is -1, then
    don't stop at all.
    """
    self.stopframe = stopframe
    self.returnframe = returnframe
    self.quitting = False
    # stoplineno >= 0 means: stop at line >= the stoplineno
    # stoplineno -1 means: don't stop at all
    self.stoplineno = stoplineno

  # Derived classes and clients can call the following methods
  # to affect the stepping state.

  def set_until(self, frame, lineno=None):
    """Stop when the line with the lineno greater than the current one is
    reached or when returning from current frame."""
    # the name "until" is borrowed from gdb
    if lineno is None:
      lineno = frame.f_lineno + 1
    self._set_stopinfo(frame, frame, lineno)

  def set_step(self):
    """Stop after one line of code."""
    # Issue #13183: pdb skips frames after hitting a breakpoint and running
    # step commands.
    # Restore the trace function in the caller (that may not have been set
    # for performance reasons) when returning from the current frame.
    if self.frame_returning:
      caller_frame = self.frame_returning.f_back
      if caller_frame and not caller_frame.f_trace:
        caller_frame.f_trace = self.trace_dispatch
    self._set_stopinfo(None, None)

  def set_next(self, frame):
    """Stop on the next line in or below the given frame."""
    self._set_stopinfo(frame, None)

  def set_return(self, frame):
    """Stop when returning from the given frame."""
    if frame.f_code.co_flags & GENERATOR_AND_COROUTINE_FLAGS:
      self._set_stopinfo(frame, None, -1)
    else:
      self._set_stopinfo(frame.f_back, frame)

  def set_trace(self, frame=None):
    """Start debugging from frame.

    If frame is not specified, debugging starts from caller's frame.
    """
    if frame is None:
      frame = sys._getframe().f_back
    self.reset()
    while frame:
      frame.f_trace = self.trace_dispatch
      self.botframe = frame
      frame = frame.f_back
    self.set_step()
    sys.settrace(self.trace_dispatch)

  def set_continue(self):
    """Stop only at breakpoints or when finished.

    If there are no breakpoints, set the system trace function to None.
    """
    # Don't stop except at breakpoints or when finished
    self._set_stopinfo(self.botframe, None, -1)
    if not self.breaks:
      # no breakpoints; run without debugger overhead
      sys.settrace(None)
      frame = sys._getframe().f_back
      while frame and frame is not self.botframe:
        del frame.f_trace
        frame = frame.f_back

  def set_quit(self):
    """Set quitting attribute to True.

    Raises BdbQuit exception in the next call to a dispatch_*() method.
    """
    self.stopframe = self.botframe
    self.returnframe = None
    self.quitting = True
    sys.settrace(None)

  # Derived classes and clients can call the following methods
  # to manipulate breakpoints.  These methods return an
  # error message if something went wrong, None if all is well.
  # Set_break prints out the breakpoint line and file:lineno.
  # Call self.get_*break*() to see the breakpoints or better
  # for bp in Breakpoint.bpbynumber: if bp: bp.bpprint().

  def set_break(self, filename, lineno, temporary=False, cond=None,
                  funcname=None):
    """Set a new breakpoint for filename:lineno.

    If lineno doesn't exist for the filename, return an error message.
    The filename should be in canonical form.
    """
    filename = self.canonic(filename)
    import linecache # Import as late as possible
    line = linecache.getline(filename, lineno)
    if not line:
      return 'Line %s:%d does not exist' % (filename, lineno)
    list = self.breaks.setdefault(filename, [])
    if lineno not in list:
      list.append(lineno)
    bp = Breakpoint(filename, lineno, temporary, cond, funcname)
    return None

  def _prune_breaks(self, filename, lineno):
    """Prune breakpoints for filename:lineno.

    A list of breakpoints is maintained in the Bdb instance and in
    the Breakpoint class.  If a breakpoint in the Bdb instance no
    longer exists in the Breakpoint class, then it's removed from the
    Bdb instance.
    """
    if (filename, lineno) not in Breakpoint.bplist:
      self.breaks[filename].remove(lineno)
    if not self.breaks[filename]:
      del self.breaks[filename]

  def clear_break(self, filename, lineno):
    """Delete breakpoints for filename:lineno.

    If no breakpoints were set, return an error message.
    """
    filename = self.canonic(filename)
    if filename not in self.breaks:
      return 'There are no breakpoints in %s' % filename
    if lineno not in self.breaks[filename]:
      return 'There is no breakpoint at %s:%d' % (filename, lineno)
    # If there's only one bp in the list for that file,line
    # pair, then remove the breaks entry
    for bp in Breakpoint.bplist[filename, lineno][:]:
      bp.deleteMe()
    self._prune_breaks(filename, lineno)
    return None

  def clear_bpbynumber(self, arg):
    """Delete a breakpoint by its index in Breakpoint.bpbynumber.

    If arg is invalid, return an error message.
    """
    try:
      bp = self.get_bpbynumber(arg)
    except ValueError as err:
      return str(err)
    bp.deleteMe()
    self._prune_breaks(bp.file, bp.line)
    return None

  def clear_all_file_breaks(self, filename):
    """Delete all breakpoints in filename.

    If none were set, return an error message.
    """
    filename = self.canonic(filename)
    if filename not in self.breaks:
      return 'There are no breakpoints in %s' % filename
    for line in self.breaks[filename]:
      blist = Breakpoint.bplist[filename, line]
      for bp in blist:
        bp.deleteMe()
    del self.breaks[filename]
    return None

  def clear_all_breaks(self):
    """Delete all existing breakpoints.

    If none were set, return an error message.
    """
    if not self.breaks:
      return 'There are no breakpoints'
    for bp in Breakpoint.bpbynumber:
      if bp:
        bp.deleteMe()
    self.breaks = {}
    return None

  def get_bpbynumber(self, arg):
    """Return a breakpoint by its index in Breakpoint.bybpnumber.

    For invalid arg values or if the breakpoint doesn't exist,
    raise a ValueError.
    """
    if not arg:
      raise ValueError('Breakpoint number expected')
    try:
      number = int(arg)
    except ValueError:
      raise ValueError('Non-numeric breakpoint number %s' % arg) from None
    try:
      bp = Breakpoint.bpbynumber[number]
    except IndexError:
      raise ValueError('Breakpoint number %d out of range' % number) from None
    if bp is None:
      raise ValueError('Breakpoint %d already deleted' % number)
    return bp

  def get_break(self, filename, lineno):
    """Return True if there is a breakpoint for filename:lineno."""
    filename = self.canonic(filename)
    return filename in self.breaks and \
      lineno in self.breaks[filename]

  def get_breaks(self, filename, lineno):
    """Return all breakpoints for filename:lineno.

    If no breakpoints are set, return an empty list.
    """
    filename = self.canonic(filename)
    return filename in self.breaks and \
      lineno in self.breaks[filename] and \
      Breakpoint.bplist[filename, lineno] or []

  def get_file_breaks(self, filename):
    """Return all lines with breakpoints for filename.

    If no breakpoints are set, return an empty list.
    """
    filename = self.canonic(filename)
    if filename in self.breaks:
      return self.breaks[filename]
    else:
      return []

  def get_all_breaks(self):
    """Return all breakpoints that are set."""
    return self.breaks

  # Derived classes and clients can call the following method
  # to get a data structure representing a stack trace.

  def get_stack(self, f, t):
    """Return a list of (frame, lineno) in a stack trace and a size.

    List starts with original calling frame, if there is one.
    Size may be number of frames above or below f.
    """
    stack = []
    if t and t.tb_frame is f:
      t = t.tb_next
    while f is not None:
      stack.append((f, f.f_lineno))
      if f is self.botframe:
        break
      f = f.f_back
    stack.reverse()
    i = max(0, len(stack) - 1)
    while t is not None:
      stack.append((t.tb_frame, t.tb_lineno))
      t = t.tb_next
    if f is None:
      i = max(0, len(stack) - 1)
    return stack, i

  def format_stack_entry(self, frame_lineno, lprefix=': '):
    """Return a string with information about a stack entry.

    The stack entry frame_lineno is a (frame, lineno) tuple.  The
    return string contains the canonical filename, the function name
    or '<lambda>', the input arguments, the return value, and the
    line of code (if it exists).

    """
    import linecache, reprlib
    frame, lineno = frame_lineno
    filename = self.canonic(frame.f_code.co_filename)
    s = '%s(%r)' % (filename, lineno)
    if frame.f_code.co_name:
      s += frame.f_code.co_name
    else:
      s += "<lambda>"
    if '__args__' in frame.f_locals:
      args = frame.f_locals['__args__']
    else:
      args = None
    if args:
      s += reprlib.repr(args)
    else:
      s += '()'
    if '__return__' in frame.f_locals:
      rv = frame.f_locals['__return__']
      s += '->'
      s += reprlib.repr(rv)
    line = linecache.getline(filename, lineno, frame.f_globals)
    if line:
      s += lprefix + line.strip()
    return s

  def print_stack_trace(self):
    try:
      for frame_lineno in self.stack:
        self.print_stack_entry(frame_lineno)
    except KeyboardInterrupt:
      pass

  # The following methods can be called by clients to use
  # a debugger to debug a statement or an expression.
  # Both can be given as a string, or a code object.

  def run(self, cmd, globals=None, locals=None):
    """Debug a statement executed via the exec() function.

    globals defaults to __main__.dict; locals defaults to globals.
    """
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
      exec(cmd, globals, locals)
    except BdbQuit:
      pass
    finally:
      self.quitting = True
      sys.settrace(None)

  def runeval(self, expr, globals=None, locals=None):
    """Debug an expression executed via the eval() function.

    globals defaults to __main__.dict; locals defaults to globals.
    """
    if globals is None:
      import __main__
      globals = __main__.__dict__
    if locals is None:
      locals = globals
    self.reset()
    sys.settrace(self.trace_dispatch)
    try:
      return eval(expr, globals, locals)
    except BdbQuit:
      pass
    finally:
      self.quitting = True
      sys.settrace(None)

  def runctx(self, cmd, globals, locals):
    """For backwards-compatibility.  Defers to run()."""
    # B/W compatibility
    self.run(cmd, globals, locals)

  # This method is more useful to debug a single function call.

  def runcall(*args, **kwds):
    """Debug a single function call.

    Return the result of the function call.
    """
    if len(args) >= 2:
      self, func, *args = args
    elif not args:
      raise TypeError("descriptor 'runcall' of 'Bdb' object "
              "needs an argument")
    elif 'func' in kwds:
      func = kwds.pop('func')
      self, *args = args
      import warnings
      warnings.warn("Passing 'func' as keyword argument is deprecated",
                          DeprecationWarning, stacklevel=2)
    else:
      raise TypeError('runcall expected at least 1 positional argument, '
              'got %d' % (len(args)-1))

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


def set_trace():
  """Start debugging with a Bdb instance from the caller's frame."""
  Bdb().set_trace()


class Breakpoint:
  """Breakpoint class.

  Implements temporary breakpoints, ignore counts, disabling and
  (re)-enabling, and conditionals.

  Breakpoints are indexed by number through bpbynumber and by
  the (file, line) tuple using bplist.  The former points to a
  single instance of class Breakpoint.  The latter points to a
  list of such instances since there may be more than one
  breakpoint per line.

  When creating a breakpoint, its associated filename should be
  in canonical form.  If funcname is defined, a breakpoint hit will be
  counted when the first line of that function is executed.  A
  conditional breakpoint always counts a hit.
  """

  # XXX Keeping state in the class is a mistake -- this means
  # you cannot have more than one active Bdb instance.

  next = 1        # Next bp to be assigned
  bplist = {}     # indexed by (file, lineno) tuple
  bpbynumber = [None] # Each entry is None or an instance of Bpt
        # index 0 is unused, except for marking an
        # effective break .... see effective()

  def __init__(self, file, line, temporary=False, cond=None, funcname=None):
    self.funcname = funcname
    # Needed if funcname is not None.
    self.func_first_executable_line = None
    self.file = file    # This better be in canonical form!
    self.line = line
    self.temporary = temporary
    self.cond = cond
    self.enabled = True
    self.ignore = 0
    self.hits = 0
    self.number = Breakpoint.next
    Breakpoint.next += 1
    # Build the two lists
    self.bpbynumber.append(self)
    if (file, line) in self.bplist:
      self.bplist[file, line].append(self)
    else:
      self.bplist[file, line] = [self]

  def deleteMe(self):
    """Delete the breakpoint from the list associated to a file:line.

    If it is the last breakpoint in that position, it also deletes
    the entry for the file:line.
    """

    index = (self.file, self.line)
    self.bpbynumber[self.number] = None   # No longer in list
    self.bplist[index].remove(self)
    if not self.bplist[index]:
      # No more bp for this f:l combo
      del self.bplist[index]

  def enable(self):
    """Mark the breakpoint as enabled."""
    self.enabled = True

  def disable(self):
    """Mark the breakpoint as disabled."""
    self.enabled = False

  def bpprint(self, out=None):
    """Print the output of bpformat().

    The optional out argument directs where the output is sent
    and defaults to standard output.
    """
    if out is None:
      out = sys.stdout
    print(self.bpformat(), file=out)

  def bpformat(self):
    """Return a string with information about the breakpoint.

    The information includes the breakpoint number, temporary
    status, file:line position, break condition, number of times to
    ignore, and number of times hit.

    """
    if self.temporary:
      disp = 'del  '
    else:
      disp = 'keep '
    if self.enabled:
      disp = disp + 'yes  '
    else:
      disp = disp + 'no   '
    ret = '%-4dbreakpoint   %s at %s:%d' % (self.number, disp,
                        self.file, self.line)
    if self.cond:
      ret += '\n\tstop only if %s' % (self.cond,)
    if self.ignore:
      ret += '\n\tignore next %d hits' % (self.ignore,)
    if self.hits:
      if self.hits > 1:
        ss = 's'
      else:
        ss = ''
      ret += '\n\tbreakpoint already hit %d time%s' % (self.hits, ss)
    return ret

  def __str__(self):
    "Return a condensed description of the breakpoint."
    return 'breakpoint %s at %s:%s' % (self.number, self.file, self.line)

# -----------end of Breakpoint class----------


def checkfuncname(b, frame):
  """Return True if break should happen here.

  Whether a break should happen depends on the way that b (the breakpoint)
  was set.  If it was set via line number, check if b.line is the same as
  the one in the frame.  If it was set via function name, check if this is
  the right function and if it is on the first executable line.
  """
  if not b.funcname:
    # Breakpoint was set via line number.
    if b.line != frame.f_lineno:
      # Breakpoint was set at a line with a def statement and the function
      # defined is called: don't break.
      return False
    return True

  # Breakpoint set via function name.
  if frame.f_code.co_name != b.funcname:
    # It's not a function call, but rather execution of def statement.
    return False

  # We are in the right frame.
  if not b.func_first_executable_line:
    # The function is entered for the 1st time.
    b.func_first_executable_line = frame.f_lineno

  if b.func_first_executable_line != frame.f_lineno:
    # But we are not at the first line number: don't break.
    return False
  return True


# Determines if there is an effective (active) breakpoint at this
# line of code.  Returns breakpoint number or 0 if none
def effective(file, line, frame):
  """Determine which breakpoint for this file:line is to be acted upon.

  Called only if we know there is a breakpoint at this location.  Return
  the breakpoint that was triggered and a boolean that indicates if it is
  ok to delete a temporary breakpoint.  Return (None, None) if there is no
  matching breakpoint.
  """
  possibles = Breakpoint.bplist[file, line]
  for b in possibles:
    if not b.enabled:
      continue
    if not checkfuncname(b, frame):
      continue
    # Count every hit when bp is enabled
    b.hits += 1
    if not b.cond:
      # If unconditional, and ignoring go on to next, else break
      if b.ignore > 0:
        b.ignore -= 1
        continue
      else:
        # breakpoint and marker that it's ok to delete if temporary
        return (b, True)
    else:
      # Conditional bp.
      # Ignore count applies only to those bpt hits where the
      # condition evaluates to true.
      try:
        val = eval(b.cond, frame.f_globals, frame.f_locals)
        if val:
          if b.ignore > 0:
            b.ignore -= 1
            # continue
          else:
            return (b, True)
        # else:
        #   continue
      except:
        # if eval fails, most conservative thing is to stop on
        # breakpoint regardless of ignore count.  Don't delete
        # temporary, as another hint to user.
        return (b, False)
  return (None, None)


# -------------------- testing --------------------

class Tdb(Bdb):
    def user_call(self, frame, args):
        name = frame.f_code.co_name
        if not name: name = '???'
        print('+++ call', name, args)
    def user_line(self, frame):
        import linecache
        name = frame.f_code.co_name
        if not name: name = '???'
        fn = self.canonic(frame.f_code.co_filename)
        line = linecache.getline(fn, frame.f_lineno, frame.f_globals)
        print('+++', fn, frame.f_lineno, name, ':', line.strip())
    def user_return(self, frame, retval):
        print('+++ return', retval)
    def user_exception(self, frame, exc_stuff):
        print('+++ exception', exc_stuff)
        self.set_continue()

def foo(n):
    print('foo(', n, ')')
    x = bar(n*10)
    print('bar returned', x)

def bar(a):
    print('bar(', a, ')')
    return a/2

def test():
    t = Tdb()
    t.run('import bdb; bdb.foo(10)')


# =============== NOTE: from test_bdb.py ===============

class Tracer(Bdb):
  """A tracer for testing the bdb module."""

  def __init__(self, expect_set, skip=None, dry_run=False, test_case=None):
    super().__init__(skip=skip)
    self.expect_set = expect_set
    self.dry_run = dry_run
    self.header = ('Dry-run results for %s:' % test_case if
                       test_case is not None else None)
    self.init_test()

  def init_test(self):
    self.cur_except = None
    self.expect_set_no = 0
    self.breakpoint_hits = None
    self.expected_list = list(islice(self.expect_set, 0, None, 2))
    self.set_list = list(islice(self.expect_set, 1, None, 2))

  def trace_dispatch(self, frame, event, arg):
    # On an 'exception' event, call_exc_trace() in Python/ceval.c discards
    # a BdbException raised by the Tracer instance, so we raise it on the
    # next trace_dispatch() call that occurs unless the set_quit() or
    # set_continue() method has been invoked on the 'exception' event.
    if self.cur_except is not None:
      raise self.cur_except

    if event == 'exception':
      try:
        res = super().trace_dispatch(frame, event, arg)
        return res
      except BdbException as e:
        self.cur_except = e
        return self.trace_dispatch
    else:
      return super().trace_dispatch(frame, event, arg)

  def user_call(self, frame, argument_list):
    # Adopt the same behavior as pdb and, as a side effect, skip also the
    # first 'call' event when the Tracer is started with Tracer.runcall()
    # which may be possibly considered as a bug.
    if not self.stop_here(frame):
      return
    self.process_event('call', frame, argument_list)
    self.next_set_method()

  def user_line(self, frame):
    self.process_event('line', frame)

    if self.dry_run and self.breakpoint_hits:
      info = info_breakpoints().strip('\n')
      # Indent each line.
      for line in info.split('\n'):
        print('  ' + line)
    self.delete_temporaries()
    self.breakpoint_hits = None

    self.next_set_method()

  def user_return(self, frame, return_value):
    self.process_event('return', frame, return_value)
    self.next_set_method()

  def user_exception(self, frame, exc_info):
    self.exc_info = exc_info
    self.process_event('exception', frame)
    self.next_set_method()

  def do_clear(self, arg):
    # The temporary breakpoints are deleted in user_line().
    bp_list = [self.currentbp]
    self.breakpoint_hits = (bp_list, bp_list)

  def delete_temporaries(self):
    if self.breakpoint_hits:
      for n in self.breakpoint_hits[1]:
        self.clear_bpbynumber(n)

  def pop_next(self):
    self.expect_set_no += 1
    try:
      self.expect = self.expected_list.pop(0)
    except IndexError:
      raise BdbNotExpectedError(
        'expect_set list exhausted, cannot pop item %d' %
        self.expect_set_no)
    self.set_tuple = self.set_list.pop(0)

  def process_event(self, event, frame, *args):
    # Call get_stack() to enable walking the stack with set_up() and
    # set_down().
    tb = None
    if event == 'exception':
      tb = self.exc_info[2]
    self.get_stack(frame, tb)

    # A breakpoint has been hit and it is not a temporary.
    if self.currentbp is not None and not self.breakpoint_hits:
      bp_list = [self.currentbp]
      self.breakpoint_hits = (bp_list, [])

    # Pop next event.
    self.event= event
    self.pop_next()
    if self.dry_run:
      self.print_state(self.header)
      return

    # Validate the expected results.
    if self.expect:
      self.check_equal(self.expect[0], event, 'Wrong event type')
      self.check_lno_name()

    if event in ('call', 'return'):
      self.check_expect_max_size(3)
    elif len(self.expect) > 3:
      if event == 'line':
        bps, temporaries = self.expect[3]
        bpnums = sorted(bps.keys())
        if not self.breakpoint_hits:
          self.raise_not_expected(
            'No breakpoints hit at expect_set item %d' %
            self.expect_set_no)
        self.check_equal(bpnums, self.breakpoint_hits[0],
          'Breakpoint numbers do not match')
        self.check_equal([bps[n] for n in bpnums],
          [self.get_bpbynumber(n).hits for
            n in self.breakpoint_hits[0]],
          'Wrong breakpoint hit count')
        self.check_equal(sorted(temporaries), self.breakpoint_hits[1],
          'Wrong temporary breakpoints')

      elif event == 'exception':
        if not isinstance(self.exc_info[1], self.expect[3]):
          self.raise_not_expected(
            "Wrong exception at expect_set item %d, got '%s'" %
            (self.expect_set_no, self.exc_info))

  def check_equal(self, expected, result, msg):
    if expected == result:
      return
    self.raise_not_expected("%s at expect_set item %d, got '%s'" %
                (msg, self.expect_set_no, result))

  def check_lno_name(self):
    """Check the line number and function co_name."""
    s = len(self.expect)
    if s > 1:
      lineno = self.lno_abs2rel()
      self.check_equal(self.expect[1], lineno, 'Wrong line number')
    if s > 2:
      self.check_equal(self.expect[2], self.frame.f_code.co_name,
                        'Wrong function name')

  def check_expect_max_size(self, size):
    if len(self.expect) > size:
      raise BdbSyntaxError('Invalid size of the %s expect tuple: %s' %
                                 (self.event, self.expect))

  def lno_abs2rel(self):
    fname = self.canonic(self.frame.f_code.co_filename)
    lineno = self.frame.f_lineno
    return ((lineno - self.frame.f_code.co_firstlineno + 1)
      if fname == self.canonic(__file__) else lineno)

  def lno_rel2abs(self, fname, lineno):
    return (self.frame.f_code.co_firstlineno + lineno - 1
      if (lineno and self.canonic(fname) == self.canonic(__file__))
      else lineno)

  def get_state(self):
    lineno = self.lno_abs2rel()
    co_name = self.frame.f_code.co_name
    state = "('%s', %d, '%s'" % (self.event, lineno, co_name)
    if self.breakpoint_hits:
      bps = '{'
      for n in self.breakpoint_hits[0]:
        if bps != '{':
          bps += ', '
        bps += '%s: %s' % (n, self.get_bpbynumber(n).hits)
      bps += '}'
      bps = '(' + bps + ', ' + str(self.breakpoint_hits[1]) + ')'
      state += ', ' + bps
    elif self.event == 'exception':
      state += ', ' + self.exc_info[0].__name__
    state += '), '
    return state.ljust(32) + str(self.set_tuple) + ','

  def print_state(self, header=None):
    if header is not None and self.expect_set_no == 1:
      print()
      print(header)
    print('%d: %s' % (self.expect_set_no, self.get_state()))

  def raise_not_expected(self, msg):
    msg += '\n'
    msg += '  Expected: %s\n' % str(self.expect)
    msg += '  Got:      ' + self.get_state()
    raise BdbNotExpectedError(msg)

  def next_set_method(self):
    set_type = self.set_tuple[0]
    args = self.set_tuple[1] if len(self.set_tuple) == 2 else None
    set_method = getattr(self, 'set_' + set_type)

    # The following set methods give back control to the tracer.
    if set_type in ('step', 'continue', 'quit'):
      set_method()
      return
    elif set_type in ('next', 'return'):
      set_method(self.frame)
      return
    elif set_type == 'until':
      lineno = None
      if args:
        lineno = self.lno_rel2abs(self.frame.f_code.co_filename,
                                          args[0])
      set_method(self.frame, lineno)
      return

    # The following set methods do not give back control to the tracer and
    # next_set_method() is called recursively.
    if (args and set_type in ('break', 'clear', 'ignore', 'enable',
                  'disable')) or set_type in ('up', 'down'):
      if set_type in ('break', 'clear'):
        fname, lineno, *remain = args
        lineno = self.lno_rel2abs(fname, lineno)
        args = [fname, lineno]
        args.extend(remain)
        set_method(*args)
      elif set_type in ('ignore', 'enable', 'disable'):
        set_method(*args)
      elif set_type in ('up', 'down'):
        set_method()

      # Process the next expect_set item.
      # It is not expected that a test may reach the recursion limit.
      self.event= None
      self.pop_next()
      if self.dry_run:
        self.print_state()
      else:
        if self.expect:
          self.check_lno_name()
        self.check_expect_max_size(3)
      self.next_set_method()
    else:
      raise BdbSyntaxError('"%s" is an invalid set_tuple' %
                                 self.set_tuple)

class TracerRun():
  """Provide a context for running a Tracer instance with a test case."""

  def __init__(self, test_case, skip=None):
    self.test_case = test_case
    self.dry_run = test_case.dry_run
    self.tracer = Tracer(test_case.expect_set, skip=skip,
                          dry_run=self.dry_run, test_case=test_case.id())
    self._original_tracer = None

  def __enter__(self):
    # test_pdb does not reset Breakpoint class attributes on exit :-(
    reset_Breakpoint()
    self._original_tracer = sys.gettrace()
    return self.tracer

  def __exit__(self, type_=None, value=None, traceback=None):
    reset_Breakpoint()
    sys.settrace(self._original_tracer)

    not_empty = ''
    if self.tracer.set_list:
      not_empty += 'All paired tuples have not been processed, '
      not_empty += ('the last one was number %d' %
                    self.tracer.expect_set_no)

    # Make a BdbNotExpectedError a unittest failure.
    if type_ is not None and issubclass(BdbNotExpectedError, type_):
      if isinstance(value, BaseException) and value.args:
        err_msg = value.args[0]
        if not_empty:
          err_msg += '\n' + not_empty
        if self.dry_run:
          print(err_msg)
          return True
        else:
          self.test_case.fail(err_msg)
      else:
        assert False, 'BdbNotExpectedError with empty args'

    if not_empty:
      if self.dry_run:
        print(not_empty)
      else:
        self.test_case.fail(not_empty)
