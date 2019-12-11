import sys, os, io, linecache, collections, inspect, threading, stackprinter, jsonpickle, copyreg, traceback, logging, optparse, contextlib, operator, json
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
from hdlogger.serializers import pickleable_dispatch
from hdlogger.utils import *

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
  'count',
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

class PickleableEnviron:
  def __init__(self, kwds):
    d = {}
    for k,v in kwds.items():
      setattr(self, k, kwds[k])

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
      "count": st.count,
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

class PickleableGenerator:
  def __init__(self,state,f_locals,pid):
    self.state = state
    self.locals = f_locals
    self.pid = pid

  def __str__(self):
    state, f_locals, pid = self.state, self.locals, self.pid
    s = f"<generator object: state={state}, locals={f_locals}, id={pid}>"
    return s

def pickle_generator(gen):
  kwds = {
    'state': inspect.getgeneratorstate(gen),
    'f_locals': inspect.getgeneratorlocals(gen),
    'pid': hex(id(gen))
  }
  return unpickle_generator, (kwds,)

def unpickle_generator(kwds):
  return PickleableGenerator(**kwds)

def getcodecontext(frame,lineno,context=2):
  if context > 0:
    start = lineno - 1 - context//2
    try:
      lines, lnum = inspect.findsource(frame)
    except OSError:
      lines = count = None
    else:
      start = max(0, min(start, len(lines) - context))
      lines = lines[start:start+context]
      count = lineno - 1 - start
  else:
    lines = count = None
  return lines, count

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
    # (Mapping, pickleable_dict)
  ]
  for special_case in special_cases:
    copyreg.pickle(*special_case)

def safer_repr(obj):
  try:
    return repr(obj)
  except:
    return f"{obj.__module__}.{obj.__class__.__name__}"

def print_attrs(obj):
  attrnames = [attr for attr in dir(obj) if not attr.startswith('_')]
  _ = operator.attrgetter(*attrnames)
  attrvals = [getattr(obj,name) for name in attrnames]
  d = {k:v for k,v in zip(attrnames,attrvals)}
  cpprint(d)
  return d

class StateFormatter:
  def __init__(
    self,
    count, filename, lineno, event, indent, symbol,
    function=None, arg=None, source=None):
    self.count = f"{count:>5}"
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
      f"{self.count}|{self.filename}:{self.lineno}|{self.event}|"
      f"{self.indent}|{self.symbol}|"
      f"{line.rstrip()}|"
    )
    return s

# TODO
class PickleableFrame:
  def __init__(self, kwds):
    self.filename = kwds['filename']
    self.lineno = kwds['lineno']
    self.function = kwds['function']
    self.local_vars = kwds['local_vars']
    self.code_context = kwds['code_context']
    self.count = kwds['count']

  def __str__(self,color=False):
    return pformat(self.__dict__)

class PickleableFrame:
  def __init__(self, kwds):
    self.filename = kwds['filename']
    self.lineno = kwds['lineno']
    self.function = kwds['function']
    self.local_vars = kwds['local_vars']
    self.code_context = kwds['code_context']
    self.count = kwds['count']

  def __str__(self,color=False):
    return pformat(self.__dict__)

def pickle_frame(frame):
  kwds = {
    "filename": frame.f_code.co_filename,
    "lineno": frame.f_lineno,
    "function": frame.f_code.co_name,
    "local_vars": frame.f_code.co_names,
    "code_context": getcodecontext(frame,frame.f_lineno)[0],
    "count": getcodecontext(frame,frame.f_lineno)[1],
  }
  return unpickle_frame, (kwds,)

def unpickle_frame(kwds):
  return PickleableFrame(kwds)

def make_pickleable_frame(frame):
  kwds = {
    "filename": frame.f_code.co_filename,
    "lineno": frame.f_lineno,
    "function": frame.f_code.co_name,
    "local_vars": frame.f_code.co_names,
    "code_context": getcodecontext(frame,frame.f_lineno)[0],
    "count": getcodecontext(frame,frame.f_lineno)[1],
  }
  return PickleableFrame(kwds)

class PickleableState:
  def __init__(self, kwds):
    self.attrs = list(kwds.keys())
    self.frame: PickleableFrame = kwds['frame']
    self.event: str = kwds['event']
    self.arg: Any = kwds['arg']
    self.f_locals: Dict = kwds['f_locals']
    self.count: int = kwds['count']
    self.function: str = kwds['function']
    self.module: str = kwds['module']
    self.filename: str = kwds['format_filename']
    self.lineno: int = kwds['lineno']
    self.stdlib: bool = kwds['stdlib']
    self.source: str = kwds['source']

  def __str__(self):
    l = []
    for attr in self.attrs:
      l.append(f"{attr}={getattr(self,attr,'None')}")
    s = "\n".join(l)
    return s

  def __iter__(self):
    yield from self.asdict().items()

  def asdict(self):
    return self.__dict__

  @property
  def indent(self):
    idt = '\u0020' * (len(PickleableState.stack)-1)
    return idt

  stack = []
  @cached_property
  def format_call(self):
    symbol = "=>"
    PickleableState.stack.append(f"{self.module}.{self.function}")
    self.formatter1 = ( # default formatter
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
      f"{self.indent}|{symbol}|{self.function}|{self.f_locals}"
    )
    self.formatter2 = ( # indented formatter
      f"{self.indent}|{symbol}|{self.function}|{self.f_locals}|"
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
    )
    self.formatter3 = ( # just sauce
      f"{self.indent}|{symbol}|{self.function}|{self.f_locals}|"
    )
    return self.formatter3

  @cached_property
  def format_line(self):
    symbol = "  "
    self.formatter1 = ( # default formatter
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
      f"{self.indent} |{symbol}|{self.source.rstrip()}|"
    )
    self.formatter2 = ( # indented formatter
      f"{self.indent} |{symbol}|{self.source.rstrip()}|"
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
    )
    self.formatter3 = ( # just sauce
      f"{self.indent} |{symbol}|{self.source.rstrip()}|"
    )
    return self.formatter3

  @cached_property
  def format_return(self):
    symbol = "<="
    self.formatter1 = ( # default formatter
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
      f"{self.indent}|{symbol}|{self.function}|{self.arg}"
    )
    self.formatter2 = ( # indented formatter
      f"{self.indent}|{symbol}|{self.function}|{self.arg}|"
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
    )
    self.formatter3 = ( # just savce
      f"{self.indent}|{symbol}|{self.function}|{self.arg}|"
    )
    if PickleableState.stack and PickleableState.stack[-1] == f"{self.module}.{self.function}":
      PickleableState.stack.pop()
    return self.formatter3

  @cached_property
  def format_exception(self):
    symbol = " !"
    self.formatter1 = ( # default formatter
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
      f"{self.indent}|{symbol}|{self.function}|{self.arg}"
    )
    self.formatter2 = ( # indented formatter
      f"{self.indent}|{symbol}|{self.function}|{self.arg}|"
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
    )
    self.formatter3 = ( # just savce
      f"{self.indent}|{symbol}|{self.function}|{self.arg}|"
    )
    return self.formatter3

def get_pickleable_state(state) -> PickleableState:
  kwds = {
      "frame": pickleable_dispatch(state.frame),
      "event": state.event,
      "arg": pickleable_dispatch(state.arg),
      "f_locals": pickleable_dispatch(state.frame.f_locals),
      "count": state.count,
      "function": state.function,
      "module": state.module,
      "format_filename": state.format_filename,
      "lineno": state.lineno,
      "stdlib": state.stdlib,
      "source": state.source,
    }
  try:
    pickleable_state = PickleableState(kwds)
  except:
    wf(stackprinter.format(sys.exc_info()),'logs/get_pickleable_state.log','a')
    raise SystemExit
  return pickleable_state

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
    self.count = next(State.counter)
    self.initialize()

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
    raise NotImplementedError("Must implement PickleableState.format_call")

  @property
  def format_line(self):
    raise NotImplementedError("Must implement PickleableState.format_line")

  @property
  def format_return(self):
    raise NotImplementedError("Must implement PickleableState.format_return")

  @property
  def format_exception(self):
    raise NotImplementedError("Must implement PickleableState.format_exception")

class HiDefTracer:

  def __init__(self):
    self.state = None
    self.pickleable_state = None
    self.pickleable_states = []
    self.pickled_state_as_bytes = []
    self.pickled_state_as_hex = []
    self.dataframe = None

  def initialize(self, frame, event, arg):
    def debug_pickleable_state(state):
      ps = self.pickleable_state
      psd = state.__dict__
      psg = ((k,psd.get(k,"nope")) for k in psd)
      for k,v in psg:
        try: pickle.loads(pickle.dumps(v))
        except:
          sys.settrace(None)
          s = stackprinter.format(sys.exc_info())
          wf(s, f"logs/{__name__}.log",'a')
          import IPython; IPython.embed()
          raise SystemExit(f"HiDefTracer.initialize.{__name__}")
      # ((k,v) for k,v in psd.items())
    initialize_copyreg()
    self.state = State(frame,event,arg)
    try:
      self.pickleable_state = get_pickleable_state(self.state)
      _as_dict = self.pickleable_state.asdict()
      _as_bytes = pickle.dumps(self.pickleable_state)
      _as_hexad = _as_bytes.hex()
      wf(pformat(_as_dict)+"\n",'logs/02.pickleable_states.tracer.log', 'a')
    except:
      debug_pickleable_state()
      raise SystemExit("shouldnt be here")
    wf(_as_hexad+"\n","logs/03.pickled_states_hex.tracer.log","a")
    self.pickleable_states.append(self.pickleable_state)

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
      pickleable = self.pickleable_state.f_locals
    except:
      wf( stackprinter.format(sys.exc_info()),'logs/tracer.dispatch_call.log', 'a')
      raise

    self.user_call(frame, pickleable)
    return self.trace_dispatch

  def dispatch_line(self, frame, arg):
    assert arg is None, f"dispatch_line: {(arg is None)=}"
    try:
      pickleable = self.pickleable_state.f_locals
    except:
      wf( stackprinter.format(sys.exc_info()),'logs/tracer.dispatch_line.log', 'a')
      raise

    self.user_line(frame, pickleable)
    return self.trace_dispatch

  def dispatch_return(self, frame, arg):
    """note: there are a few `special cases` wrt `arg`"""
    if arg is None: return ""
    try:
      pickleable = self.pickleable_state.arg
    except:
      wf( stackprinter.format(sys.exc_info()),'logs/tracer.dispatch_return.log', 'a')
      raise

    self.user_return(frame, pickleable)
    return self.trace_dispatch

  def dispatch_exception(self, frame, arg):
    if arg is None: return ""
    try:
      pickleable = self.pickleable_state.arg
    except:
      wf( stackprinter.format(sys.exc_info()),'logs/tracer.dispatch_exc.log', 'a')
      raise

    self.user_exception(frame, pickleable)
    return self.trace_dispatch

  def user_call(self, frame, argument_list):
    logging.debug('user_call')
    try:
      print(self.pickleable_state.format_call)
    except:
      sys.settrace(None)
      wf(stackprinter.format(sys.exc_info()),'logs/tracer.user_call.log','a')
      from ipdb import set_trace as st; st()
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

def main():
  from tester.helpers import final_selector
  t = HiDefTracer()
  t.run(final_selector)


if __name__ == '__main__':
  main()

# f = inspect.currentframe()
# pf = make_pickleable_frame(f)
# kwds = dict(
#     frame=pf,
#     event='call',
#     arg=None,
#     f_locals={'a':12},
#     count=43,
#     function="wefa",
#     module="mod",
#     format_filename="wetwfge",
#     lineno=43,
#     stdlib=False,
#     source='f = inspect.currentframe()\n',
# )
# pst = PickleableState(kwds)
# print(pst)

# pst
