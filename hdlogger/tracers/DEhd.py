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
from hdlogger.serializers import pickleable_dispatch, initialize_copyreg, State, make_pickleable_state
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

def print_attrs(obj):
  attrnames = [attr for attr in dir(obj) if not attr.startswith('_')]
  _ = operator.attrgetter(*attrnames)
  attrvals = [getattr(obj,name) for name in attrnames]
  d = {k:v for k,v in zip(attrnames,attrvals)}
  cpprint(d)
  return d

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
      self.pickleable_state = make_pickleable_state(self.state)
      _as_dict = self.pickleable_state.asdict()
      _as_bytes = pickle.dumps(self.pickleable_state)
      _as_hexad = _as_bytes.hex()
      wf(pformat(_as_dict)+"\n",'logs/02.pickleable_states.tracer.log', 'a')
    except:
      debug_pickleable_state(self.state)
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
