import sys, os, io, linecache, collections, inspect, threading, stackprinter, jsonpickle, copyreg, traceback, logging
import dill as pickle
from pickle import PicklingError
# dill.Pickler.dispatch
from prettyprinter import pformat
from collections import namedtuple
from itertools import count
from functools import singledispatchmethod, cached_property
from pathlib import Path
from typing import Callable, Iterable
from types import FunctionType, GeneratorType, FrameType
from bdb import BdbQuit
from hunter.const import SYS_PREFIX_PATHS
from pydantic import ValidationError
from inspect import CO_GENERATOR, CO_COROUTINE, CO_ASYNC_GENERATOR
from ..data_structures import TraceHookCallbackException, TraceHookCallbackReturn, PickleableDict

GENERATOR_AND_COROUTINE_FLAGS = CO_GENERATOR | CO_COROUTINE | CO_ASYNC_GENERATOR # 672
WRITE = True
def ws(spaces=0,tabs=0):
  indent_size = spaces + (tabs * 2)
  whitespace_character = " "
  return f"{whitespace_character * indent_size}"

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

def write_file(obj,filename,mode='w'):
  with open(filename,mode) as f:
    f.write(obj)

def first_true(iterable, default=False, pred=None):
    """Returns the first true value in the iterable.

    If no true value is found, returns *default*

    If *pred* is not None, returns the first item
    for which pred(item) is true.

    """
    # first_true([a,b,c], x) --> a or b or c or x
    # first_true([a,b], x, f) --> a if f(a) else b if f(b) else x
    return next(filter(pred, iterable), default)

def pickle_generator(gen):
  kwds = {
    'state': inspect.getgeneratorstate(gen),
    'locals': inspect.getgeneratorlocals(gen),
    'id': hex(id(gen))
  }
  return unpickle, (kwds,)

def pickle_frame(frame):
  kwds = {'f_fileno':frame.f_lineno}
  return unpickle, (kwds,)

def unpickle(kwds):
  Unpickleable = type('Unpickleable',(), dict.fromkeys(kwds))
  return Unpickeable(**kwds)

def initialize_copyreg():
  special_cases = [
    (GeneratorType,pickle_generator),
    (FrameType,pickle_frame),
  ]
  for special_case in special_cases:
    copyreg.pickle(*special_case)

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

def safer_repr(obj):
  try:
    return repr(obj)
  except:
    return f"{obj.__module__}.{obj.__class__.__name__}"

class State:
  SYS_PREFIX_PATHS = set((
    sys.prefix,
    sys.exec_prefix,
    os.path.dirname(os.__file__),
    os.path.dirname(collections.__file__),
  ))
  counter = count(0)

  def __init__(self, frame, event, arg):
    with open('logs/state.raw_arg.log','w') as f:
      f.write(repr(arg)+"\n")
    self.frame = frame
    self.event = event
    self.arg = arg if arg else ""
    self.index = next(State.counter)
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
    initialize_copyreg()
    self.serialized_arg = self.serialize_arg()

  def serialize_arg(self):
    if self.event == "return" and self.arg is not None:
      self.arg = TraceHookCallbackReturn(**{'return_value':self.arg})

    if self.event == "exception" and self.arg is not None:
      try:
        kwds = dict(zip(['etype','value','tb'], self.arg))
        self.arg = TraceHookCallbackException(**kwds)
      except:
        with open('logs/serialize_arg.exc.log','a') as f:
          f.write(stackprinter.format(sys.exc_info()))
        raise

    if self.event == "call":
      assert not self.arg, f"{self.arg=}"
      try:
        kwds = self.frame.f_locals
        self.arg = PickleableDict(**kwds)
        with open('logs/state.seriaize_arg.log','w') as f:
          f.write(str(self.arg))
      except:
        with open('logs/serialize_arg.call.log','a') as f:
          f.write(stackprinter.format(sys.exc_info()))
        raise

    try:
      _as_bytes = pickle.dumps(self.arg)
      assert pickle.loads(_as_bytes), f"{pickle.loads(_as_bytes)}"
    except:
      _as_json = jsonpickle.encode(self.arg)
      _as_bytes = pickle.dumps(_as_json)
      assert pickle.loads(_as_bytes), f"{pickle.loads(_as_bytes)}"

    _as_hex = _as_bytes.hex()
    assert pickle.loads(bytes.fromhex(_as_hex)), f"{pickle.loads(bytes.fromhex(_as_hex))}"
    with open('logs/state.serialized_arg.log','a') as f: f.write(_as_hex+"\n")
    return _as_hex

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
    assert isinstance(self.arg,PickleableDict), f"{self.arg=}\n{self.frame.f_locals.keys()=}"
    argvars = dict(self.arg)
    self.formatter = StateFormatter(
      self.index, self.format_filename, self.lineno,
      self.event, "\u0020" * (len(State.stack)-1), "=>",
      function=self.function, arg=dict(self.arg))
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
      function=f"{self.function}: ", arg=self.arg)
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
      function=f"{self.function}: ", arg=self.arg)
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
    self.return_values = []
    self.serialized_data = []
    initialize_copyreg()

  def deserialize(self, bytesfile='logs/state.serialized_arg.log'):
    """Load each item that was previously written to disk."""
    with open(bytesfile,'r') as f:
      _lines_as_hex = f.readlines()
    l = []
    for i,line in enumerate(_lines_as_hex):
      try:
        print(i,line)
        _as_bytes = bytes.fromhex(line)
        deserialized = pickle.loads(_as_bytes)
      except:
        with open('logs/deserialize.err.log','a') as f:
          f.write(f"{i=}\n{line=}\n\n")
          f.write(stackprinter.format(sys.exc_info()))
        raise
      l.append(deserialized)
      with open('logs/tracer.deserialized_arg.log','a') as f:
        f.write(str(deserialized)+"\n")
    return l

  def trace_dispatch(self, frame, event, arg):
    with open('logs/tracer.arg.log','a') as f: f.write(repr(arg)+'\n')
    self.state = State(frame,event,arg)
    # if self.quitting:
      # return # None
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
    self.user_call(frame, arg)
    return self.trace_dispatch

  def dispatch_line(self, frame, arg):
    assert arg is None, f"dispatch_line: {(arg is None)=}"
    self.user_line(frame)
    return self.trace_dispatch

  def dispatch_return(self, frame, arg):
    """note: there are a few `special cases` wrt `arg`"""
    if arg is not None:
      try:
        # with open('logs/dispatch_return.log','a') as f: f.write(str(arg))
        kwds = {'return_value': arg}
        TraceHookCallbackReturn(**kwds)
      except ValidationError as e:
        print(e.json())
        raise
      except:
        print(stackprinter.format(sys.exc_info()))
        raise
    self.user_return(frame, arg)
    return self.trace_dispatch

  def dispatch_exception(self, frame, arg):
    self.user_exception(frame, arg)
    return self.trace_dispatch

  def user_call(self, frame, argument_list):
    print('user_call')
    print(self.state.format_call)
    return self.trace_dispatch

  def user_line(self, frame):
    print('user_line')
    print(self.state.format_line)
    return self.trace_dispatch

  def user_return(self, frame, return_value):
    print('user_return')
    print(self.state.format_return)
    if return_value:
      assert self.state.arg.return_value == return_value, f"{self.state.arg=}, {return_value=}"
      self.return_values.append(return_value)

  def user_exception(self, frame, exc_info):
    print('user_exception')
    print(self.state.format_exception)
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



