import sys, os, io, linecache, collections, inspect, threading, stackprinter, jsonpickle, copyreg, traceback, logging, optparse, contextlib, operator
import dill as pickle
import pandas as pd
from pickle import PicklingError
# dill.Pickler.dispatch
from prettyprinter import pformat, cpprint
from collections import namedtuple
from itertools import count
from functools import singledispatchmethod, cached_property
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence
from types import FunctionType, GeneratorType, FrameType, TracebackType
from bdb import BdbQuit
from hunter.const import SYS_PREFIX_PATHS
from pydantic import ValidationError
from inspect import CO_GENERATOR, CO_COROUTINE, CO_ASYNC_GENERATOR
from ..data_structures import (
  TraceHookCallbackCall, TraceHookCallbackLine, TraceHookCallbackReturn, TraceHookCallbackException,
)

GENERATOR_AND_COROUTINE_FLAGS = CO_GENERATOR | CO_COROUTINE | CO_ASYNC_GENERATOR # 672
WRITE = True

def check(func,arg):
  with contextlib.suppress(Exception):
    return func(arg)

def wf(filename,obj,mode="a"):
  with open(filename,mode) as f:
    f.write(obj)

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

def funk_works(funk,arg):
  try: return funk(arg)
  except: return None

def apply_funcs(funcs,arg):
  """return the first working func"""
  for func in funcs:
    try:
      rv = func(arg)
      pickle.pickles(rv)
      return rv
    except:
      pass
  raise

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


def pickleable_dispatch(obj):
  if isinstance(obj,Iterable) and not isinstance(obj,str):
    if isinstance(obj, Mapping):
      return pickleable_dict(obj)
    elif isinstance(obj, Sequence):
      return pickleable_list(obj)
    else:
      with open('logs/models.pickleable_dispatch.log','w') as f:
        f.write(stackprinter.format(sys.exc_info()))
      raise
  elif isinstance(obj,FrameType):
    return pickleable_frame(obj)
  else:
    return pickleable_simple(obj)

def pickleable_frame(frm):
  try:
    return pickle.loads(pickle.dumps(frm))
  except:
    wf('logs/pickleable_frame.tracer.log', stackprinter.format(sys.exc_info()))
    raise

def pickleable_dict(d):
  def check(func,arg):
    with contextlib.suppress(Exception):
      return func(arg)

  try:
    return pickle.loads(pickle.dumps(d))
  except:
    print(2)
    d2 = {}
    funclist = [lambda v: pickle.loads(pickle.dumps(v)), lambda v: jsonpickle.encode(v),lambda v: getattr(v,'__class__.__name__')]
    for k,v in d.items():
      try:
        checked = [check(func,v) for func in funclist]
        pickleable = next(filter(None,checked))
        d2[k] = pickleable
      except:
        with open('logs/tracer.pickleable_dict.log','a') as f:
          f.write(f"{k=}: {type(v)=}\n\n")
          f.write(stackprinter.format())
        raise
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
          with open('logs/models.unpickleable.log','a') as f:
            f.write(stackprinter.format(sys.exc_info()))
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
    with open('logs/models.unpickleable.log','a') as f:
      f.write(stackprinter.format(sys.exc_info()))
    raise SystemExit


def pickle_generator(gen):
  kwds = {
    'state': inspect.getgeneratorstate(gen),
    'locals': inspect.getgeneratorlocals(gen),
    'id': hex(id(gen))
  }
  return unpickle_generator, (kwds,)

def unpickle_generator(kwds):
  return Unpickleable(**kwds)

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

class PickleableTraceback:
  def __init__(self,lasti,lineno):
    self.lasti = lasti
    self.lineno = lineno

def pickle_traceback(tb):
  kwds = {
    'lasti': tb.tb_lasti,
    'lineno':tb.tb_lineno,
  }
  return unpickle_traceback, (kwds,)

def unpickle_traceback(kwds):
  return PickleableTraceback(**kwds)

def unpickle(kwds):
  Unpickleable = type('Unpickleable',(), dict.fromkeys(kwds))
  return Unpickleable(**kwds)

class PickleableOptparseOption:
  def __init__(self,module,classname):
    self.module = module
    self.classname = classname
    self.id = id(self)  #  0x%x:

  def __str__(self):
    # s = f"{obj.__module__}.{obj.__class__.__name__}"
    s = f"{self.module}.{self.classname}"
    return s

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
    (GeneratorType,pickle_generator),
    (FrameType,pickle_frame),
    (TracebackType,pickle_traceback),
    (optparse.Option,pickle_optparse_option),
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


import copyreg
def print_attrs(obj):
  attrnames = [attr for attr in dir(obj) if not attr.startswith('_')]
  _ = operator.attrgetter(*attrnames)
  attrvals = [getattr(obj,name) for name in attrnames]
  d = {k:v for k,v in zip(attrnames,attrvals)}
  cpprint(d)
  return d


def util():
  f_locals = self.frame.f_locals
  f_code = self.frame.f_code
  keys = f_locals.keys()
  dispatch_table = copyreg.dispatch_table
  pickle_func = dispatch_table[type(f_locals)]

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
    self._serialized_arg = None
    self._serialized_locals = None
    initialize_copyreg()
    self.pickleable_locals = pickleable_dict(self.frame.f_locals)
    self.pickleable_arg = pickleable_dispatch(self.arg)
    self.pickleable_frame = pickleable_dispatch(self.frame)
    self.serialized_locals = self.serialize_locals()
    self.serialized_arg = self.serialize_arg()

  def serialize_arg(self):
    if self._serialized_arg: return self._serialized_arg
    _as_bytes = pickle.dumps(self.pickleable_arg)
    _as_hex = _as_bytes.hex()
    with open('logs/serialized_arg.state.log','w') as f:
      f.write(_as_hex+"\n")
    self._serialized_arg = _as_hex
    return self._serialized_arg

  @property
  def pickleable_vars(self):
    """provide a commin interace for the event kinds"""
    PickleableVars = namedtuple('PickleableVars', 'arg locals')
    pvs = PickleableVars(self.pickleable_arg, self.pickleable_locals)
    return pvs

  def serialize_locals(self):
    if self._serialized_locals: return sekf._serialized_locals
    _as_bytes = pickle.dumps(self.pickleable_locals)
    _as_hex = _as_bytes.hex()
    with open('logs/tracer.serialized_locals.log','w') as f:
      f.write(_as_hex+"\n")
    self._serialized_locals = _as_hex
    return self._serialized_locals

  @cached_property
  def format_filename(self):
    if not isinstance(self.filename,Path):
      filename = Path(self.filename)
    stem = f"{filename.stem:>10.10}"
    return stem

  @property
  def pickleable_vars(self):
    d = {'locals': self.pickleable_locals,
    'arg': self.pickleable_arg}
    return d

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
    self.history = []
    self.dataframe = None
    initialize_copyreg()

  def make_dataframe(self):
    if bool(self.dataframe): return self.dataframe
    states = self.history
    fields = ['frame',
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
      'function_object',
      'module',
      'filename',
      'lineno',
      'code',
      'stdlib',
      'source',
      'format_filename',
      # 'formatter'
      ]
      # TODO: each "state" in `states` is len=17, for the 17 fields (len(fields))
    pickleable_states = []
    for state in states:
      field_values = operator.attrgetter(*fields)
      pickleable_state = dict(zip(fields, field_values(state)))
      # assert bool(pickle.pickles(pickleable_state)), f"{bool(pickle.pickles(pickleable_state))}"
      pickleable_states.append(pickleable_state)
    # assert all([pickle.loads(pickle.dumps(pst)) for pst in pickleable_states]), f"{pickleable_states=}"
    for i,r in enumerate(pickleable_states):
      try:
        pickleable_state = pickle.loads(pickle.dumps(r))
      except:
        with open('logs/make_dataframe.rowerr.log','a') as f:
          f.write(stackprinter.format(sys.exc_info()))
        raise SystemExit
    df = pd.DataFrame(pickleable_states,columns=fields)
    self.dataframe = df
    df_pkl_pth = Path("logs/dataframe.tracer.pkl")
    try:
      df.to_pickle(str(df_pkl_pth)) # df works here
    except:
      # triangulate the edrror source
      r1 = df.iloc[0]
      r1d = dict(r1)
      res = [check(elm) for elm in r1]
      raise
    # assert bool(pd.read_pickle(df_pkl_pth)), "can't pickle df"
    return df

  def save_history(self):
    histpath = Path("logs/serialized_states.tracer.log")
    for state in self.history:
      _as_bytes = pickle.dumps(state)
      _as_hex = _as_bytes.hex()
      with open(histpath,'a') as f:
        f.write(_as_hex + "\n")
    assert histpath.exists()

  def load_history(self):
    states = []
    with open("logs/serialized_states.tracer.log",'r') as f:
      lines = f.readlines()
    _as_bytes = [bytes.fromhex(line) for line in lines]
    _as_obj = [pickle.loads(_bytes) for _bytes in _as_bytes]
    return _as_obj

  def trace_dispatch(self, frame, event, arg):
    with open('logs/tracer.arg.log','a') as f:
      f.write(repr(arg)+'\n')
    self.state = State(frame,event,arg)
    pre = len(self.history)
    self.history.append(self.state)
    assert len(self.history)-1 == pre, "!"*8
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
    try:
      pickleable = self.state.pickleable_locals
    except ValidationError as e:
      with open('logs/tracer.dispatch_call.log','a') as f:
        f.write(stackprinter.format(sys.exc_info()))
      raise

    self.user_call(frame, pickleable)
    return self.trace_dispatch

  def dispatch_line(self, frame, arg):
    assert arg is None, f"dispatch_line: {(arg is None)=}"
    try:
      pickleable = self.state.pickleable_locals
    except ValidationError as e:
      with open('logs/tracer.dispatch_line.log','a') as f:
        f.write(stackprinter.format(sys.exc_info()))
      raise

    self.user_line(frame, pickleable)
    return self.trace_dispatch

  def dispatch_return(self, frame, arg):
    """note: there are a few `special cases` wrt `arg`"""
    if arg is None: return ""
    try:
      pickleable = self.state.pickleable_arg
    except ValidationError as e:
      with open('logs/tracer.dispatch_line.log','a') as f:
        f.write(stackprinter.format(sys.exc_info()))
      raise

    self.user_return(frame, pickleable)
    return self.trace_dispatch

  def dispatch_exception(self, frame, arg):
    if arg is None: return ""
    try:
      pickleable = self.state.pickleable_arg
    except ValidationError as e:
      with open('logs/tracer.dispatch_exc.log','a') as f:
        f.write(stackprinter.format(sys.exc_info()))
      raise

    self.user_exception(frame, pickleable)
    return self.trace_dispatch

  def user_call(self, frame, argument_list):
    logging.debug('user_call')
    print(self.state.format_call)
    return self.trace_dispatch

  def user_line(self, frame, pickleable):
    logging.debug('user_line')
    print(self.state.format_line)
    return self.trace_dispatch

  def user_return(self, frame, return_value):
    logging.debug('user_return')
    print(self.state.format_return)

  def user_exception(self, frame, exc_info):
    logging.debug('user_exception')
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


