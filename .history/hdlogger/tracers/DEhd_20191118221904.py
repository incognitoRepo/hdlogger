class HiDefTracer:

  def __init__(self):
    pass

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
      expr = cmd
      return eval(expr, globals, locals)
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

