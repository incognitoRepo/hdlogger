import sys, os, io, linecache, collections, inspect, threading, stackprinter, jsonpickle, copyreg, traceback, logging, optparse, contextlib, operator, json, operator, re
import dill as pickle
import pandas as pd
from pickle import PicklingError
# dill.Pickler.dispatch
from prettyprinter import pformat, cpprint
from collections import namedtuple, defaultdict
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
from hdlogger.serializers import pickleable_dispatch, initialize_copyreg, State, make_pickleable_state, PickleableState
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

def predicate(frame):
  code = frame.f_code
  filename = code.co_filename
  return 'youtube' in filename

def filtered_function(funcname):
  filtered_functions = [
    'add_info_extractor','add_default_info_extractors',
    'extract_info',
  ]
  for ff in filtered_functions:
    if m:=re.match(ff,funcname):
      wf(f"{ff=}\n{funcname=}\n{m=}\n\n",'logs/filtered_function.true.log','a')
      return True
    else:
      wf(f"{ff=}\n{funcname=}\n\n",'logs/filtered_function.false.log','a')
  return False

def filtered_filename(filename):
  filtered_filenames = [
    r'.*common.py$',r'.*sre_parse/.py$',
    r'.*options.py$',r'.*extractor/.py$',
  ]
  name:str = Path(filename).resolve().name
  for ff in filtered_filenames:
    if m:=re.match(ff,filename):
      return True
    else:
      pass
  return False

@singledispatch
def arg_shortcut_preprocess(arg):
  try:
    modname = inspect.getmodule(arg).__name__
  except:
    return arg
  else:
    if hasattr(arg,'__module__') and modname == 'ctypes':
      return repr(arg)
    return arg

@arg_shortcut_preprocess.register
def _(arg:dict):
  nd = {}
  for k,v in arg.items():
    try:
      modename = inspect.getmodule(arg).__name__
    except:
      nd.update({k:v})
    else:
      if hasattr(arg,'__module__') and modname == 'ctypes':
        nd.update({k:repr(v)})
      return nd.update({k:v})

class VariablesWatcher:

  def __init__(self,variables:List[str]):
    self.variables = variables
    self.d = defaultdict(list)

  def check_assumptions(self,frame,event,arg):
    # f_locals is a strict subset of f_globals
    # gkeys,lkeys = set(frame.f_globals.keys()),set(frame.f_locals.keys()) # doesn't hold
    # assert lkeys.issubset(gkeys), f"{lkeys.symmetric_difference(gkeys)}"
    # code assumptions
    code = frame.f_code
    # nb. node.co_argcount is < varnames and nlocls
    if not (len(code.co_varnames) == code.co_nlocals):
      raise SystemExit(f"assumption failed: {len(code.co_varnames)=}, {code.co_nlocals=}")

  def check_event(self,frame,event,arg):
    self.check_assumptions(frame,event,arg)
    gkeys,lkeys = list(frame.f_globals.keys()), list(frame.f_locals.keys())
    results = [(var in gkeys) for var in self.variables]
    for var in self.variables:
      if var in lkeys:
        val = frame.f_locals[var]
      elif var in gkeys:
        val = frame.f_globals[var]
      else:
        continue
      self.d[var].append(
        [val, frame.f_lineno, frame.f_code.co_name, frame.f_code.co_filename]
      )
    return self.d

  def write_var_history(self):
    l = []
    for k,v in self.d.items():
      val, lno, fnc, filename = v
      l.append(f"{filename:10.10}{fnc:10.10}{lno:<05}\n\t{k}={v}\n")
    s = '\n'.join(l)
    wf(s,'logs/vars_watcher.log','a')
    return s

class HiDefTracer:

  def __init__(self):
    self.state = None
    self.pickleable_state = None
    self.pickleable_states = []
    self.pickled_state_as_bytes = []
    self.pickled_state_as_hex = []
    self.dataframe = None

  def trace_dispatch(self, frame, event, arg):
    """this is the entry point for this class"""
    if not frame: sys.settrace(None); return None
    if not predicate(frame): return None
    if filtered_function(frame.f_code.co_name):
      return None
    if filtered_filename(frame.f_code.co_filename):
      return None
    try:
      assert self.initialize(frame, event, arg) # ears1
    except:
      wf( stackprinter.format(sys.exc_info()),'logs/tracer.dispatch.log', 'a')
      raise

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

  def initialize(self, frame, event, arg):
    arg = arg_shortcut_preprocess(arg)
    if hasattr(arg,'__module__') and arg.__module__ == 'ctypes':
      wf(f'2. {type(arg)=}, {arg=}\n', 'logs/DEhd.initialize.138.log', 'a')
      initialize_copyreg(Type2Add=type(arg))
    else:
      initialize_copyreg()
    self.state = State(frame,event,arg)
    try:
      self.pickleable_state = make_pickleable_state(self.state, PickleableState._stack) # ears2 -> transformers.44
    except:
      wf( stackprinter.format(sys.exc_info()),'logs/cant.make.log', 'a')
      raise
    else:
      _as_dict = self.pickleable_state.asdict()
      _as_bytes = pickle.dumps(self.pickleable_state)
      _as_hexad = _as_bytes.hex()
    wf(_as_hexad+"\n","logs/03.pickled_states_hex.tracer.log","a") # TODO: must uncomment
    self.pickleable_states.append(self.pickleable_state)
    return True

  def dispatch_call(self, frame, arg):
    assert arg is None, f"dispatch_call: {(arg is None)=}"
    try:
      pickleable = self.pickleable_state.f_locals
    except:
      wf(stackprinter.format(sys.exc_info()),'logs/tracer.dispatch_call.log', 'a')
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
    if arg is None: arg = 'None'
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
      pkl = pickle.dumps(self.pickleable_state.pkl_format_call)
      hexa = pkl.hex()
      wf(hexa, 'logs/tracer.user_call.pkl', 'a')
      # print(self.pickleable_state.format_call.strip())
    except:
      wf(stackprinter.format(sys.exc_info()),'logs/tracer.user_call.log','a')
      raise
    return self.trace_dispatch

  def user_line(self, frame, pickleable):
    logging.debug('user_line')
    try:
      pkl = pickle.dumps(self.pickleable_state.pkl_format_line)
      hexa = pkl.hex()
      wf(hexa, 'logs/tracer.user_line.pkl', 'a')
      # print(self.pickleable_state.format_line.strip())
    except:
      wf(stackprinter.format(sys.exc_info()),'logs/tracer.user_line.log''a')
      raise
    return self.trace_dispatch

  def user_return(self, frame, return_value):
    logging.debug('user_return')
    try:
      pkl = pickle.dumps(self.pickleable_state.pkl_format_return)
      hexa = pkl.hex()
      wf(hexa, 'logs/tracer.user_return.pkl', 'a')
      # print(self.pickleable_state.format_return.strip())
    except:
      wf(stackprinter.format(sys.exc_info()),'logs/user_return','a')
      raise

  def user_exception(self, frame, exc_info):
    logging.debug('user_exception')
    try:
      pkl = pickle.dumps(self.pickleable_state.pkl_format_exception)
      hexa = pkl.hex()
      wf(hexa, 'logs/tracer.user_exception.pkl', 'a')
      # print(self.pickleable_state.format_exception.strip())
    except:
      wf(stackprinter.format(sys.exc_info()),'logs/user_exception','a')
      raise
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


# class PickleableFrame:
#   """recreate the entire frame"""
#   def __init__(self):
#     pass
