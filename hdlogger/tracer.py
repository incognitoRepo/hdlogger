# vscode-fold=1
class _Ignore:
  """from trace module"""
  def __init__(self, modules=None, dirs=None):
    self._mods = set() if not modules else set(modules)
    self._dirs = [] if not dirs else [os.path.normpath(d)
                                      for d in dirs]
    self._ignore = { '<string>': 1 }

  def names(self, filename, modulename):
    if modulename in self._ignore:
      return self._ignore[modulename]

    # haven't seen this one before, so see if the module name is
    # on the ignore list.
    if modulename in self._mods:  # Identical names, so ignore
      self._ignore[modulename] = 1
      return 1

    # check if the module is a proper submodule of something on
    # the ignore list
    for mod in self._mods:
        # Need to take some care since ignoring
        # "cmp" mustn't mean ignoring "cmpcache" but ignoring
        # "Spam" must also mean ignoring "Spam.Eggs".
        if modulename.startswith(mod + '.'):
          self._ignore[modulename] = 1
          return 1

    # Now check that filename isn't in one of the directories
    if filename is None:
        # must be a built-in, so we must ignore
      self._ignore[modulename] = 1
      return 1

    # Ignore a file when it contains one of the ignorable paths
    for d in self._dirs:
        # The '+ os.sep' is to ensure that d is a parent directory,
        # as compared to cases like:
        #  d = "/usr/local"
        #  filename = "/usr/local.py"
        # or
        #  d = "/usr/local.py"
        #  filename = "/usr/local.py"
        if filename.startswith(d + os.sep):
          self._ignore[modulename] = 1
          return 1

    # Tried the different ways, so we don't ignore this module
    self._ignore[modulename] = 0
    return 0

class Tracer:
  """from trace module"""
  def __init__(self,ignoremods=(),ignoredirs=(),infile=None,outfile=None,timing=True):
    self.infile=infile
    self.outfile=outfile
    self.ignore = _Ignore(ignoremods,ignoredirs)
    self.counts = {}
    self.pathtobasename = {}
    self._calledfuncs = {}
    self._callers = {}
    self._caller_cache = {}
    self.start_time = None
    if timing:
      self.start_time = _time()
    self.globaltrace = self.globaltrace_lt
    self.localtrace = self.localtrace_trace_and_count

  def run(self, cmd):
    import __main__
    dict = __main__.__dict__
    # assert len(globals().keys()) >= len(locals().keys()) == len(__main__.__dict__.keys()), f"{globals().keys()=}\n{locals().keys()=}\n{__main__.__dict__.keys()=}"
    self.runctx(cmd, dict, dict)

  def runctx(self, cmd, globals=None, locals=None):
    if globals is None: globals = {}
    if locals is None: locals = {}
    threading.settrace(self.globaltrace)
    sys.settrace(self.globaltrace)
    try:
      exec(cmd, globals, locals)
    finally:
      sys.settrace(None)
      threading.settrace(None)

  def runfunc(*args, **kw):
    if len(args) >= 2:
      self, func, *args = args
    elif not args:
      raise TypeError("descriptor 'runfunc' of 'Trace' object needs an argument")
    elif 'func' in kw:
      func = kw.pop('func')
      self, *args = args
      import warnings
      warnings.warn("Passing 'func' as keyword argument is deprecated",
                    DeprecationWarning, stacklevel=2)
    else:
      raise TypeError('runfunc expected at least 1 positional argument, '
                      'got %d' % (len(args)-1))

    result = None
    sys.settrace(self.globaltrace)
    try:
      result = func(*args, **kw)
    finally:
      sys.settrace(None)
    return result
  runfunc.__text_signature__ = '($self, func, /, *args, **kw)'

  def globaltrace_lt(self, frame, why, arg):
    """Handler for call events.

    If the code block being entered is to be ignored, returns `None',
    else returns self.localtrace
    """
    # XXX (o for o in [1]) # test_sys_settraace traceWithgenexp
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
            print(f" --- modulename: {modulename}, funcname: {code.co_name}")
            return self.localtrace
      else:
        return None

  def localtrace_trace_and_count(self, frame, why, arg):
    """returns the new local trace function

    events: call, line, exception, opcode (i.e., !return)
    "What do you want the trace function to be next?"
    """
    if why == "line":
      # record the file name and line number of every trace
      filename = frame.f_code.co_filename
      lineno = frame.f_lineno
      key = filename, lineno
      self.counts[key] = self.counts.get(key, 0) + 1

      if self.start_time:
        print('%.2f' % (_time() - self.start_time), end=' ')
      bname = os.path.basename(filename)
      print("%s(%d): %s" % (bname, lineno,
                            linecache.getline(filename, lineno)), end='')
    return self.localtrace

  def results(self):
    return CoverageResults(self.counts,
      infile=self.infile,outfile=self.outfile)

class CoverageResults:
  """from trace module"""
  def __init__(self, counts=None, infile=None,
               callers=None, outfile=None):
    self.counts = counts
    if self.counts is None:
      self.counts = {}
    self.counter = self.counts.copy() # map (filename, lineno) to count
    self.callers = callers
    if self.callers is None:
      self.callers = {}
    self.callers = self.callers.copy()
    self.infile = infile
    self.outfile = outfile
    if self.infile:
      # Try to merge existing counts file.
      try:
        with open(self.infile, 'rb') as f:
          counts, calledfuncs, callers = pickle.load(f)
        self.update(self.__class__(counts, calledfuncs, callers))
      except (OSError, EOFError, ValueError) as err:
        print(("Skipping counts file %r: %s"
                                      % (self.infile, err)), file=sys.stderr)

  def is_ignored_filename(self, filename):
    """Return True if the filename does not refer to a file
    we want to have reported.
    """
    return filename.startswith('<') and filename.endswith('>')

  def update(self, other):
    """Merge in the data from another CoverageResults"""
    counts = self.counts
    calledfuncs = self.calledfuncs
    callers = self.callers
    other_counts = other.counts
    other_calledfuncs = other.calledfuncs
    other_callers = other.callers

    for key in other_counts:
      counts[key] = counts.get(key, 0) + other_counts[key]

    for key in other_calledfuncs:
      calledfuncs[key] = 1

    for key in other_callers:
      callers[key] = 1

  def write_results(self, show_missing=True, summary=False, coverdir=None):
    """
    Write the coverage results.

    :param show_missing: Show lines that had no hits.
    :param summary: Include coverage summary per module.
    :param coverdir: If None, the results of each module are placed in its
                         directory, otherwise it is included in the directory
                         specified.
    """
    # turn the counts data ("(filename, lineno) = count") into something
    # accessible on a per-file basis
    per_file = {}
    for filename, lineno in self.counts:
      lines_hit = per_file[filename] = per_file.get(filename, {})
      lines_hit[lineno] = self.counts[(filename, lineno)]

    # accumulate summary info, if needed
    sums = {}

    for filename, count in per_file.items():
      if self.is_ignored_filename(filename):
        continue

      if filename.endswith(".pyc"):
        filename = filename[:-1]

      if coverdir is None:
        dir = os.path.dirname(os.path.abspath(filename))
        modulename = _modname(filename)
      else:
        dir = coverdir
        if not os.path.exists(dir):
          os.makedirs(dir)
        modulename = _fullmodname(filename)

      # If desired, get a list of the line numbers which represent
      # executable content (returned as a dict for better lookup speed)
      if show_missing:
        lnotab = _find_executable_linenos(filename)
      else:
        lnotab = {}
      source = linecache.getlines(filename)
      coverpath = os.path.join(dir, modulename + ".cover")
      with open(filename, 'rb') as fp:
        encoding, _ = tokenize.detect_encoding(fp.readline)
      n_hits, n_lines = self.write_results_file(coverpath, source,
                                                      lnotab, count, encoding)
      if summary and n_lines:
        percent = int(100 * n_hits / n_lines)
        sums[modulename] = n_lines, percent, modulename, filename

    if summary and sums:
      print("lines   cov%   module   (path)")
      for m in sorted(sums):
        n_lines, percent, modulename, filename = sums[m]
        print("%5d   %3d%%   %s   (%s)" % sums[m])

    if self.outfile:
      # try and store counts and module info into self.outfile
      try:
        pickle.dump((self.counts, self.calledfuncs, self.callers),
              open(self.outfile, 'wb'), 1)
      except OSError as err:
        print("Can't save counts files because %s" % err, file=sys.stderr)

  def write_results_file(self, path, lines, lnotab, lines_hit, encoding=None):
    """Return a coverage results file in path."""
    # ``lnotab`` is a dict of executable lines, or a line number "table"

    try:
      outfile = open(path, "w", encoding=encoding)
    except OSError as err:
      print(("trace: Could not open %r for writing: %s "
                                  "- skipping" % (path, err)), file=sys.stderr)
      return 0, 0

    n_lines = 0
    n_hits = 0
    with outfile:
      for lineno, line in enumerate(lines, 1):
        # do the blank/comment match to try to mark more lines
        # (help the reader find stuff that hasn't been covered)
        if lineno in lines_hit:
          outfile.write("%5d: " % lines_hit[lineno])
          n_hits += 1
          n_lines += 1
        elif lineno in lnotab and not PRAGMA_NOCOVER in line:
          # Highlight never-executed lines, unless the line contains
          # #pragma: NO COVER
          outfile.write(">>>>>> ")
          n_lines += 1
        else:
          outfile.write("       ")
        outfile.write(line.expandtabs(8))

    return n_hits, n_lines
