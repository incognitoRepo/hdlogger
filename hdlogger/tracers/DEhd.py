import sys, os, io, linecache, collections, inspect, threading, stackprinter, jsonpickle, copyreg, traceback, logging, optparse, contextlib, operator
import dill as pickle
import pandas as pd
from pickle import PicklingError
# dill.Pickler.dispatch
from prettyprinter import pformat, cpprint
from collections import namedtuple
from itertools import count
from functools import singledispatch, singledispatchmethod, cached_property
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence, Any, Dict, List, Tuple
from types import FunctionType, GeneratorType, FrameType, TracebackType, FunctionType
from bdb import BdbQuit
from hunter.const import SYS_PREFIX_PATHS
from pydantic import ValidationError
from dataclasses import dataclass
from inspect import CO_GENERATOR, CO_COROUTINE, CO_ASYNC_GENERATOR
from ..data_structures import (
  TraceHookCallbackCall, TraceHookCallbackLine, TraceHookCallbackReturn, TraceHookCallbackException,
)

GENERATOR_AND_COROUTINE_FLAGS = CO_GENERATOR | CO_COROUTINE | CO_ASYNC_GENERATOR # 672
WRITE = True

state_attrs = [
  'pickleable_frame',
  'event',
  # 'arg',
  'pickleable_arg',
  'serialized_arg',
  # 'locals',
  'pickleable_locals',
  'serialized_locals',
  'index',
  # 'globals',
  'function',
  # 'function_object',
  'module',
  'filename',
  'lineno',
  # 'code',
  'stdlib',
  'source',
  'format_filename',
  # 'formatter'
  ]

def checkfuncs(funcs,arg):
  def checkfunc(func,arg):
    with contextlib.suppress(Exception):
      return func(arg)
  for func in funcs:
    if funcres:= checkfunc(func,arg) is not None:
      return funcres
    else:
      return None
  raise Exception("DEhd.checkfuncs: all funcs failed")

def wf(obj,filename,mode="a"):
  path = Path(filename)
  if not path.parent.exists():
    path.mkdir(parents=True, exist_ok=True)
  if isinstance(obj, bytes):
    obj = str(obj)
  elif isinstance(obj, Iterable):
    if isinstance(obj, str):
      pass
    else:
      obj = "\n".join(str(obj)) + "\n"
  with path.open(mode,encoding="utf-8") as f:
    f.write(str(obj))

def rf(filename, mode="r"):
  path = Path(filename)
  with open(path, mode) as f:
    lines = f.readlines()
  return lines

def whitespace(spaces=0,tabs=0): # ws
  indent_size = spaces + (tabs * 2)
  whitespace_character = " "
  return f"{whitespace_character * indent_size}"
ws = whitespace

def _c(s,modifier=0,intensity=3,color=0):
  """
  mod      ::= 0(reset)|1(bold)|2(faint)|3(italic)|4(underline)
  int      ::= 9(intense fg) | 3(normal bg)
  clr      ::= 0(blk)|1(red)|2(grn)|3(ylw)|4(blu)|5(mag)|6(cyn)|7(wht)
  """
  escape = "\x1b["
  reset_modifier = 0
  ns = f"{escape}{modifier};{intensity}{color}m{s}{escape}{reset_modifier}m"
  return ns

def c(s,arg=None):
  if WRITE is True: return s
  """apply color to a string"""
  if s == 'call': return _c(s,modifier=1,intensity=9,color=2)
  if s == 'line': return _c(s,modifier=2,intensity=3,color=0)
  if s == 'return': return _c(s,modifier=1,intensity=9,color=3)
  if s == 'exception': return _c(s,modifier=1,intensity=9,color=1)

  if arg:
    if arg == 'vars': return _c(s,modifier=0,intensity=9,color=5)
    # symbols
    if arg == 'call': return _c(s,modifier=1,intensity=9,color=2)
    if arg == 'line': return _c(s,modifier=2,intensity=3,color=0)
    if arg == 'return': return _c(s,modifier=1,intensity=9,color=3)
    if arg == 'exception': return _c(s,modifier=1,intensity=9,color=1)

def first_true(iterable, default=False, pred=None):
    """Returns the first true value in the iterable.

    If no true value is found, returns *default*

    If *pred* is not None, returns the first item
    for which pred(item) is true.

    """
    # first_true([a,b,c], x) --> a or b or c or x
    # first_true([a,b], x, f) --> a if f(a) else b if f(b) else x
    return next(filter(pred, iterable), default)

def make_state_dict():
  dict(zip(attrs,map(attrgetter,attrs)))

def pickleable_dispatch(obj):
  try:
    return pickle.loads(pickle.dumps(obj))
  except:
    if isinstance(obj, bytes): obj = str(obj)
    if isinstance(obj,Iterable) and not isinstance(obj,str):
      if isinstance(obj, Mapping):
        return pickleable_dict(obj)
      elif isinstance(obj, Sequence):
        return pickleable_list(obj)
      else:
        wf(stackprinter.format(sys.exc_info()),'logs/models.pickleable_dispatch.log','a')
        raise
    elif isinstance(obj,FrameType):
      return pickleable_frame(obj)
    else:
      return pickleable_simple(obj)
    s = stackprinter.format(sys.exc_info())
    print(s)
    raise SystemExit(f"failure in pickleable_dispatch: cannot pickle {obj}")

def pickleable_environ(env):
  envd = dict(env)
  try:
    return pickleable_dict(envd)
  except:
    wf( stackprinter.format(sys.exc_info()),'logs/pickleable_env.tracer.log', 'a')
    raise

def pickleable_frame(frm):
  try:
    return pickle.loads(pickle.dumps(frm))
  except:
    wf('logs/pickleable_frame.tracer.log', stackprinter.format(sys.exc_info()))
    raise

def pickleable_dict(d):
  funclist = [
    lambda v: pickle.loads(pickle.dumps(v)),
    lambda v: jsonpickle.encode(v),
    lambda v: getattr(v,'__class__.__name__')
  ]
  d2 = {}
  for k,v in d.items():
    try:
      checked = checkfuncs(funclist,v)
      pickleable = next(filter(None,checked))
      d2[k] = pickleable
    except:
      s = stackprinter.format(sys.exc_info())
      wf( s,'logs/pickleable_dict.tracers.log',mode="a")

      raise SystemExit(f"unable to pickle {d} due to:\n{k=}\n{v=}")
  return d2

def pickleable_globals(g):
  cp = g.copy()
  cp['__builtins__'] = "-removed-"
  g2 = pickleable_dict(cp)
  return g2

def pickleable_list(l):
  if l == "": return ""
  try:
    ddl = pickle.dumps(l)
    assert pickle.loads(ddl)
    return l
  except:
      l2 = []
      for elm in l:
        try:
          dde = pickle.dumps(elm)
          assert pickle.loads(dde), f"cant load pickle.dumps(dde)={dde}"
          l2.append(dde)
        except:
          for test in [
            lambda: pickle.dumps(jsonpickle.encode(elm)),
            lambda: pickle.dumps(repr(elm)),
            lambda: pickle.dumps(str(elm)),
            lambda: pickle.dumps(elm.__class__.__name__)
            ]:
            try:
              dde = test()
              assert pickle.loads(dde), f"cant load pickle.dumps(dde)={dde}"
              l2.append(dde)
            except: pass
          wf( stackprinter.format(sys.exc_info()),'logs/models.unpickleable.log', 'a')
          raise SystemExit
      return l2

def pickleable_simple(s):
  if s == "": return ""
  try:
    dds = pickle.dumps(s)
    assert pickle.loads(dds)
    return s
  except:
    for test in [
      lambda: pickle.dumps(jsonpickle.encode(s)),
      lambda: pickle.dumps(repr(s)),
      lambda: pickle.dumps(str(s)),
      lambda: pickle.dumps(s.__class__.__name__)
      ]:
      try:
        dds = test()
        assert pickle.loads(dds), f"cant load pickle.dumps(dds)={dds}"
        return dds
      except:
        pass
    wf( stackprinter.format(sys.exc_info()),'logs/models.unpickleable.log', 'a')
    raise SystemExit


class StateFormatter:
  def __init__(
    self,
    index, filename, lineno, event, indent, symbol,
    function=None, arg=None, source=None):
    self.index = f"{index:>5}"
    self.filename = filename
    self.lineno = f"{lineno:<5}"
    self.event = f"{event:9} "
    self.indent = indent
    self.symbol = f"{symbol} "
    self.function = function
    self.arg = arg
    self.source = source

  def __str__(self,color=False):
    if self.source:
      line = self.source
    else:
      line = self.function + str(self.arg)

    s = (
      f"{self.index}|{self.filename}:{self.lineno}|{self.event}|"
      f"{self.indent}|{self.symbol}|"
      f"{line.rstrip()}|"
    )

    return s

class PickleableEnviron:
  def __init__(self, kwds):
    d = {}
    for k,v in kwds.items():
      setattr(self, k, kwds[k])

class PickleableGenerator:
  def __init__(self, state, locals, id):
    self.state = state
    self.locals = locals
    self.id = id

class PickleableFrame:
  def __init__(self, filename, lineno, function, local_vars, code_context, index):
    self.filename = filename
    self.lineno = lineno
    self.function = function
    self.local_vars = local_vars
    self.code_context = code_context
    self.index = index

  def __str__(self,color=False):
    return pformat(self.__dict__)

class PickleableTraceback:
  def __init__(self,lasti,lineno):
    self.lasti = lasti
    self.lineno = lineno

class GenericPickleableMapping:
  pass

class PickleableOptparseOption:
  def __init__(self,module,classname):
    self.module = module
    self.classname = classname
    self.id = id(self)  #  0x%x:

  def __str__(self):
    l = []
    for k,v in self.__dict__.items():
      l.append(f"{k}={v}")
    s = f"{self.module}.{self.classname}, {id=}"
    return s

def pickle_function(fnc):
  sig = inspect.signature(fnc)
  inspect.Signature(sig.parameters.values())
  kwds = sig.parameters
  return unpickle_function, (kwds,)

def unpickle_function(kwds):
  return inspect.Signature(kwds)

def pickle_state(st):
  kwds = {
      "frame": st.pickleable_frame,
      "event": st.event,
      "arg": st.pickleable_arg,
      "locals": st.pickleable_locals,
      "index": st.index,
      "function": st.function,
      "module": st.module,
      "filename": st.filename,
      "lineno": st.lineno,
      "stdlib": st.stdlib,
      "source": st.source,
      "format_filename": st.format_filename,
  }
  return unpickle_state, (kwds,)

def unpickle_state(kwds):
  return PickleableState(**kwds)

def pickle_generator(gen):
  kwds = {
    'state': inspect.getgeneratorstate(gen),
    'locals': inspect.getgeneratorlocals(gen),
    'id': hex(id(gen))
  }
  return unpickle_generator, (kwds,)

def unpickle_generator(kwds):
  return PickableGenerator(**kwds)

def getcodecontext(frame,lineno,context=2):
  if context > 0:
    start = lineno - 1 - context//2
    try:
      lines, lnum = inspect.findsource(frame)
    except OSError:
      lines = index = None
    else:
      start = max(0, min(start, len(lines) - context))
      lines = lines[start:start+context]
      index = lineno - 1 - start
  else:
    lines = index = None
  return lines, index

def pickle_frame(frame):
  kwds = {
    "filename": frame.f_code.co_filename,
    "lineno": frame.f_lineno,
    "function": frame.f_code.co_name,
    "local_vars": frame.f_code.co_names,
    "code_context": getcodecontext(frame,frame.f_lineno)[0],
    "index": getcodecontext(frame,frame.f_lineno)[1],
  }
  return unpickle_frame, (kwds,)

def unpickle_frame(kwds):
  return PickleableFrame(**kwds)

def pickle_traceback(tb):
  kwds = {
    'lasti': tb.tb_lasti,
    'lineno':tb.tb_lineno,
  }
  return unpickle_traceback, (kwds,)

def unpickle_traceback(kwds):
  return PickleableTraceback(**kwds)

def pickle_optparse_option(optopt):
  """str(pickle.loads(pickle.dumps(self)))"""
  kwds = {
    'module':optopt.__module__,
    'classname':optopt.__class__.__name__,
  }
  return unpickle_optparse_option, (kwds,)

def unpickle_optparse_option(kwds):
  return PickleableOptparseOption(**kwds)

def initialize_copyreg():
  special_cases = [
    (GeneratorType, pickle_generator),
    (FrameType, pickle_frame),
    (TracebackType, pickle_traceback),
    (optparse.Option, pickle_optparse_option),
    (State, pickle_state),
    (FunctionType, pickle_function),
    (Mapping, pickleable_dict)
  ]
  for special_case in special_cases:
    copyreg.pickle(*special_case)

def safer_repr(obj):
  try:
    return repr(obj)
  except:
    return f"{obj.__module__}.{obj.__class__.__name__}"


import copyreg
def print_attrs(obj):
  attrnames = [attr for attr in dir(obj) if not attr.startswith('_')]
  _ = operator.attrgetter(*attrnames)
  attrvals = [getattr(obj,name) for name in attrnames]
  d = {k:v for k,v in zip(attrnames,attrvals)}
  cpprint(d)
  return d


@dataclass
class PickleableState:
  frame: PickleableFrame
  event: str
  arg: Any
  locals: Dict
  index: int
  function: str
  module: str
  filename: str
  lineno: int
  stdlib: bool
  source: str
  format_filename: str

  def __str__(self):
    l = []
    attrs = self.__annotations__.keys()
    for attr in attrs:
      l.append(f"{attr}={getattr(self,attr,'None')}")
    s = "\n".join(l)
    return s

  stack = []
  @cached_property
  def format_call(self):
    PickleableState.stack.append(f"{self.module}.{self.function}")
    self.formatter = StateFormatter(
      self.index, self.format_filename, self.lineno,
      self.event, "\u0020" * (len(PickleableState.stack)-1), "=>",
      function=self.function, arg=self.locals)
    return str(self.formatter)

  @cached_property
  def format_line(self):
    self.formatter = StateFormatter(
      self.index, self.format_filename, self.lineno,
      self.event, "\u0020" * len(PickleableState.stack), "  ",
      source=self.source)
    return str(self.formatter)

  @cached_property
  def format_return(self):
    self.formatter = StateFormatter(
      self.index, self.format_filename, self.lineno,
      self.event, "\u0020" * (len(PickleableState.stack)-1), "<=",
      function=f"{self.function}: ", arg=self.arg)
    if PickleableState.stack and PickleableState.stack[-1] == f"{self.module}.{self.function}":
      PickleableState.stack.pop()
    return str(self.formatter)

  @cached_property
  def format_exception(self):
    self.formatter = StateFormatter(
      self.index, self.format_filename, self.lineno,
      self.event, "\u0020" * (len(PickleableState.stack)-1), " !",
      function=f"{self.function}: ", arg=self.arg)
    return str(self.formatter)

class State:
  SYS_PREFIX_PATHS = set((
    sys.prefix,
    sys.exec_prefix,
    os.path.dirname(os.__file__),
    os.path.dirname(collections.__file__),))
  counter = count(0)

  def __init__(self, frame, event, arg):
    wf(repr(arg)+"\n",'logs/01.initial_arg.state.log', 'a')
    self.frame = frame
    self.event = event
    self.arg = arg
    self.index = next(State.counter)
    self.initialize()

  def get_pickleable_state(self) -> PickleableState:
    psd = {
        "frame": pickleable_dispatch(self.frame),
        "event": self.event,
        "arg": pickleable_dispatch(self.arg),
        "locals": pickleable_dispatch(self.frame.f_locals),
        "index": self.index,
        "function": self.function,
        "module": self.module,
        "filename": self.filename,
        "lineno": self.lineno,
        "stdlib": self.stdlib,
        "source": self.source,
        "format_filename": self.format_filename,
      }
    pickleable_state = PickleableState(**psd)
    return pickleable_state

  def initialize(self):
    self.locals = self.frame.f_locals
    self.globals = self.frame.f_globals
    self.function = self.frame.f_code.co_name
    self.function_object = self.frame.f_code
    self.module = self.frame.f_globals.get('__name__','')
    self.filename = self.frame.f_code.co_filename
    self.lineno = self.frame.f_lineno
    self.code = self.frame.f_code
    self.stdlib = True if self.filename.startswith(SYS_PREFIX_PATHS) else False
    self.source = linecache.getline(self.filename, self.lineno, self.frame.f_globals)
    self._call = None
    self._line = None
    self._return = None
    self._exception = None
    self._serialized_arg = None
    self._serialized_locals = None

  @cached_property
  def format_filename(self):
    if not isinstance(self.filename,Path):
      filename = Path(self.filename)
    stem = f"{filename.stem:>10.10}"
    return stem

  stack = []
  @property
  def format_call(self):
    if self._call: return self._call
    State.stack.append(f"{self.module}.{self.function}")
    self.formatter = StateFormatter(
      self.index, self.format_filename, self.lineno,
      self.event, "\u0020" * (len(State.stack)-1), "=>",
      function=self.function, arg=self.pickleable_locals)
    self._call = str(self.formatter)
    return self._call

  @property
  def format_line(self):
    if self._line: return self._line
    self.formatter = StateFormatter(
      self.index, self.format_filename, self.lineno,
      self.event, "\u0020" * len(State.stack), "  ",
      source=self.source)
    self._line = str(self.formatter)
    return self._line

  @property
  def format_return(self):
    if self._return: return self._return
    self.formatter = StateFormatter(
      self.index, self.format_filename, self.lineno,
      self.event, "\u0020" * (len(State.stack)-1), "<=",
      function=f"{self.function}: ", arg=self.pickleable_arg)
    self._return = str(self.formatter)
    if State.stack and State.stack[-1] == f"{self.module}.{self.function}":
      State.stack.pop()
    return self._return

  @property
  def format_exception(self):
    if self._return: return self._return
    self.formatter = StateFormatter(
      self.index, self.format_filename, self.lineno,
      self.event, "\u0020" * (len(State.stack)-1), " !",
      function=f"{self.function}: ", arg=self.pickleable_arg)
    self._return = str(self.formatter)
    return self._return

class StateCollection:
  def __init__(self,states):
    self._df = None
    self.initialize_states_data()
    self.states_path = (
      Path('~/VSCodeProjects')
      .expanduser()
      .joinpath('vytd/src/youtube-dl')
    )
    self.states = self.states_path.read_text()
    print(self.states)

  def df(self):
    if self._df: return self._df
    Row = namedtuple(
      'Row',
      'index filename lineno event indent symbol function arg source',
      defaults = (None, None, None),
    )
    list_of_rows = []
    for st in self.states:
      f = st.formatter
      row = Row(f.index, f.filename, f.lineno, f.event, f.indent, f.symbol, f.function, f.arg, f.source)
      list_of_rows.append(row)
    df = pd.DataFrame((row._as_dict() for row in list_of_rows))
    print(df)
    self._df = df
    return df


class HiDefTracer:

  def __init__(self):
    self.state = None
    self.pickleable_state = None
    self.pickleable_states = []
    self.pickled_state_as_bytes = []
    self.pickled_state_as_hex = []
    self.dataframe = None

  def initialize(self, frame, event, arg):
    initialize_copyreg()
    def _state(f, e, a):
      self.state = State(f,e,a)
      self.pickleable_state = self.state.get_pickleable_state()
      _as_bytes = pickle.dumps(self.pickleable_state)
      _as_hexad = _as_bytes.hex()
      wf(pformat(self.pickleable_state)+"\n",'logs/02.pickleable_states.tracer.log', 'a')
      wf(_as_hexad+"\n","logs/03.pickled_states_hex.tracer.log","a")
      self.pickleable_states.append(self.pickleable_state)
    def _dataframe():
      _state_as_dict = [self.pickleable_state.__dict__]
      self.dataframe = pd.DataFrame(_state_as_dict)
      try:
        self.dataframe.to_string('logs/dataframe.tracers.txt')
        self.dataframe.to_pickle('logs/dataframe.tracers.pkl')
        pd.Dataframe.read_pickle('logs/dataframe.tracers.pkl')
      except:
        pdd = pickle.dumps(self.dataframe)
        pld = pickle.loads(pdd)
        wf(self.dataframe, 'logs/dataframe.ERROR.log', 'a')

    _state(frame, event, arg)
    _dataframe()

  def trace_dispatch(self, frame, event, arg):
    """this is the entry point for this class"""
    self.initialize(frame, event, arg)
    if event == 'line':
      return self.dispatch_line(frame, arg)
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
    assert arg is None, f"dispatch_call: {(arg is None)=}"
    try:
      pickleable = self.pickleable_state.locals
    except ValidationError as e:
      wf( stackprinter.format(sys.exc_info()),'logs/tracer.dispatch_call.log', 'a')
      raise

    self.user_call(frame, pickleable)
    return self.trace_dispatch

  def dispatch_line(self, frame, arg):
    assert arg is None, f"dispatch_line: {(arg is None)=}"
    try:
      pickleable = self.pickleable_state.locals
    except ValidationError as e:
      wf( stackprinter.format(sys.exc_info()),'logs/tracer.dispatch_line.log', 'a')
      raise

    self.user_line(frame, pickleable)
    return self.trace_dispatch

  def dispatch_return(self, frame, arg):
    """note: there are a few `special cases` wrt `arg`"""
    if arg is None: return ""
    try:
      pickleable = self.pickleable_state.arg
    except ValidationError as e:
      wf( stackprinter.format(sys.exc_info()),'logs/tracer.dispatch_line.log', 'a')
      raise

    self.user_return(frame, pickleable)
    return self.trace_dispatch

  def dispatch_exception(self, frame, arg):
    if arg is None: return ""
    try:
      pickleable = self.pickleable_state.arg
    except ValidationError as e:
      wf( stackprinter.format(sys.exc_info()),'logs/tracer.dispatch_exc.log', 'a')
      raise

    self.user_exception(frame, pickleable)
    return self.trace_dispatch

  def user_call(self, frame, argument_list):
    logging.debug('user_call')
    print(self.pickleable_state.format_call)
    return self.trace_dispatch

  def user_line(self, frame, pickleable):
    logging.debug('user_line')
    print(self.pickleable_state.format_line)
    return self.trace_dispatch

  def user_return(self, frame, return_value):
    logging.debug('user_return')
    print(self.pickleable_state.format_return)

  def user_exception(self, frame, exc_info):
    logging.debug('user_exception')
    print(self.pickleable_state.format_exception)
    return self.trace_dispatch

  @singledispatchmethod
  def run(self, cmd, *args, **kwds):
    raise NotImplementedError

  @run.register
  def _(self, cmd:str, *args, **kwds):
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

    self.reset()
    sys.settrace(self.trace_dispatch)
    res = None
    try:
      res = cmd(**kwds)
      self.return_value = res
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

def unserialize_file(filename, mode):
  path = Path('/Users/alberthan/VSCodeProjects/HDLogger/youtube-dl/logs/tracers.pickled_states.dat')
  with open(path, mode) as f:
    lines = f.readlines()
  _as_bytes = [bytes.fromhex(line) for line in lines]
  _as_pyobj = [pickle.loads(bites) for bites in _as_bytes]


def main():
  from tester.helpers import final_selector
  t = HiDefTracer()
  t.run(final_selector)


if __name__ == '__main__':
  main()



# with open('/Users/alberthan/VSCodeProjects/HDLogger/youtube-dl/logs/initialize_df.tracers.log','r') as f:
#   idf = f.read()

# idfb = bytes.fromhex(idf)
# pyobj = pickle.loads(idfb)

# pd.read_pickle(idf)
