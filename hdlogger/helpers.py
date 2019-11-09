# vscode-fold=1
import dis, inspect, trace, os, threading, sys, linecache, tokenize
from time import monotonic as _time
import jsonpickle as jsonpkl
from pathlib import Path
from collections import namedtuple, Counter
from itertools import count, tee
from types import SimpleNamespace, GeneratorType
import stackprinter
from linecache import getline
from trace import _modname, _fullmodname, _find_executable_linenos

from typing import Dict,List,Union,Any
from types import (
  FrameType
)
from .constants import (
  SITE_PACKAGES_PATHS,
  SYS_PREFIX_PATHS,
  CYTHON_SUFFIX_RE,
  STARTSWITH_PASS_MODULES,
)

PRAGMA_NOCOVER = "#pragma NO COVER"

def filter(event_module):
  em = event_module
  for MOD in STARTSWITH_PASS_MODULES:
    if em.startswith(MOD):
      return True
  return False

def filter_only(event_module,target_modules:list):
  em = event_module
  for tmod in target_modules:
    if tmod in em:
      return True
  return False

def get_answer():
  """Get an answer."""
  return True

UNSET = object()
class Event:
  DATA = SimpleNamespace(kind="",dataset=set())
  COUNT = count()
  def __init__(
    self,
    frame:FrameType,event:str,arg:Any,
    write_flag:bool=False,
    collect_data:bool=False,
  ):
    self.frame = frame
    self.count = next(self.COUNT)
    self.module = self.frame.f_globals.get('__name__','')
    self.filename = self.frame.f_code.co_filename
    self.lineno = self.frame.f_lineno
    src = getline(self.filename, self.lineno, self.frame.f_globals)
    self.source = src
    this_func = "\x1b[2;3;96mEvent\x1b[0m"

    self.event = event
    self.test_frame(arg)
    self.arg = arg
    self.arg_type = type(arg)
    # self._code = UNSET
    # self._fullsource = UNSET
    # self._function_object = UNSET
    # self._function = UNSET
    # self._globals = UNSET
    # self._lineno = UNSET
    # self._locals = UNSET

    self._stdlib = UNSET
    # self._threadidn = UNSET
    # self._threadname = UNSET
    # self._thread = UNSET
    if collect_data: self.setup_data_collection(collect_data)
    if write_flag: self.write_trace()
    if arg:
      print(f"    in {this_func}: {self.count=}, {self.module=}, {event=}, {arg=}", end="")
      print(f", isinstance \x1b[1;34m{isinstance(arg,GeneratorType)}\x1b[0m")
    else:
      print(f"    in {this_func}: {self.count=}, {self.module=}, {event=}, {arg=}",end="")
      print(f", isinstance \x1b[1;34m{isinstance(arg,GeneratorType)}\x1b[0m")

  def test_frame(self,arg):
    if 'rv' in self.frame.f_locals:
      pass

  def test_frame1(self,arg):
    if not arg: arg = "null"
    if 'rv' in self.frame.f_locals:
      cf = inspect.currentframe()
      print(self.frame.f_locals.keys())
      print(cf.f_locals['self'].frame.f_locals.keys())
      print(list(self.frame.f_locals['rv']))
      self.frame.f_locals['rv2'] = [333]
      import ipdb; ipdb.set_trace()
      print(self.frame.f_locals.keys())
      print(list(self.frame.f_locals['rv2']))
      fl = list(self.frame.f_locals['rv2'])
      fl1,fl2,fl3 = (elm for elm in fl),(elm for elm in fl),(elm for elm in range(3))
      self.frame.f_locals['rv'] = fl3
      print(f"  {isinstance(arg,GeneratorType)=}, {list(arg)}")
      print(f"  {isinstance(fl2, GeneratorType)=}, {list(fl2)=}")
      print(f"  {list(arg)}")
      print(f"  {list(fl1)=}")
      self.frame.f_locals['rv'] = [elm for elm in range(3)]
      print(f"  {isinstance(self.frame.f_locals['rv'],GeneratorType)=}, {list(self.frame.f_locals['rv'])=}")

  def test_frame2(self,arg):
    if not arg: arg = "null"
    print(self.frame.f_globals.keys())
    if 'rv' in self.frame.f_globals:
      cf = inspect.currentframe()
      print(self.frame.f_globals.keys())
      print(cf.f_globals['self'].frame.f_globals.keys())
      print(list(self.frame.f_globals['rv']))
      self.frame.f_globals['rv2'] = [333]
      import ipdb; ipdb.set_trace()
      print(self.frame.f_globals.keys())
      print(list(self.frame.f_globals['rv2']))
      fl = list(self.frame.f_globals['rv2'])
      fl1,fl2,fl3 = (elm for elm in fl),(elm for elm in fl),(elm for elm in range(3))
      self.frame.f_globals['rv'] = fl3
      print(f"  {isinstance(arg,GeneratorType)=}, {list(arg)}")
      print(f"  {isinstance(fl2, GeneratorType)=}, {list(fl2)=}")
      print(f"  {list(arg)}")
      print(f"  {list(fl1)=}")
      self.frame.f_globals['rv'] = [elm for elm in range(3)]
      print(f"  {isinstance(self.frame.f_globals['rv'],GeneratorType)=}, {list(self.frame.f_globals['rv'])=}")

  @property
  def stdlib(self):
    if self._stdlib is UNSET:
      module_parts = self.module.split('.')
      if 'pkg_resources' in module_parts:
        self._stdlib = True
      elif self.filename == '<frozen importlib._bootstrap>':
        self._stdlib = True
      elif self.filename.startswith(SITE_PACKAGES_PATHS):
        # if it's in site-packages then its definitely not stdlib
        self._stdlib = False
      elif self.filename.startswith(SYS_PREFIX_PATHS):
        self._stdlib = True
      else:
        self._stdlib = False
    return self._stdlib

  @property
  def data(self):
    return self.DATA

  def setup_data_collection(self,which_data):
    self.DATA.kind = which_data
    self.DATA.dataset.add(getattr(self,which_data))

  def write_data(self):
    filepath = Path(f"_{self.DATA.kind}_data.log").resolve()
    with open(filepath,"w") as f:
      f.write('\n'.join([elm for elm in self.DATA.dataset if elm is not None]))
    assert filepath.exists(), f'failed to write data to {filepath}'
    return filepath

  def write_trace(self):
    pfss = get_strs(self,self.COUNT)
    jp = jsonpkl.encode(pfss)
    jsonpath = Path('_jsnpkl.json').resolve()
    # if pfss['arg']:
      # print(f'      cnt({pfss["cnt"]}): {pfss["arg"]=}')
    with open(jsonpath,'a') as f:
      f.write(jp+'\n')
    return jsonpath

def get_strs(event,counter=""):
  packed_frame_strings = {
    "cnt": event.count,
    "evt": event,
    "arg": event.arg,
    "mod": event.module,
    "frm": event.frame,
    "cod": event.frame.f_code,
    "atyp": event.arg_type,
    "dis_bc": dis.Bytecode(event.frame.f_code)
  }
  return packed_frame_strings

TracerKillPack = namedtuple(
  'TracerKillPack',
  'frame event arg'
)
def get_tracer_kill_pack():
  tkp = TracerKillPack(
    inspect.currentframe(),
    'kill',
    None)
  return tkp


class Tracer(object):

  def __init__(self, filename, append=False, record_locals=False):
    self.filename = filename
    self.file = open(filename, 'a' if append else 'w')
    self.lock = threading.Lock()
    self.enabled = False
    self.record_locals = record_locals

  def enable(self):
    if self.enabled: return
    self.enabled = True

    @wraps(thread.start_new_thread)
    def start_new_thread(func, args, kwargs={}):
      @wraps(func)
      def wrapper(*args, **kwargs):
        sys.settrace(self._handle_trace)
        return func(*args, **kwargs)
      return start_new_thread.__wrapped__(wrapper, args, kwargs)

    thread.start_new_thread = start_new_thread
    threading._start_new_thread = start_new_thread
    sys.settrace(self._handle_trace)

  def disable(self):
    if not self.enabled: return
    self.enabled = False
    thread.start_new_thread = thread.start_new_thread.__wrapped__
    threading._start_new_thread = thread._start_new_thread.__wrapped__
    sys.settrace(None)

  def _handle_trace(self, frame, event, arg, depth=0):
    data = {'timestamp': time.clock(), 'event': event, 'arg': safe_repr(arg),
            'thread': thread.get_ident(), 'filename': frame.f_code.co_filename,
            'lineno': frame.f_lineno, 'co_name': frame.f_code.co_name,
            'depth': depth}
    if self.record_locals:
      data['locals'] = json.dumps(frame.f_locals, cls=SafeJsonEncoder)
    with self.lock:
      self.file.write(json.dumps(data))
      self.file.write('\n')
      self.file.flush()
    if event == 'call':
      return functools.partial(self._handle_trace, depth=depth+1)
    return frame.f_trace or self._handle_trace

class _Ignore:
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


def trace_ex():
  tracer = trace.Trace(
    count=1,
    trace=1,
    countfuncs=0,
    countcallers=0,
    ignoremods=(),
    ignoredirs=[sys.base_prefix,sys.base_exec_prefix],
    infile=None,
    outfile=None,
    timing=False,
  )
  tracer.run('main()')
  r = tracer.results()
  r.write_results(show_missing=True,summary=True,coverdir="/tmp")
