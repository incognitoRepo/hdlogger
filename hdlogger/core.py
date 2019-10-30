# -*- coding: utf-8 -*-
# vscode-fold=1
import dis, sys, inspect
from ipdb import set_trace as st
from itertools import tee
from types import GeneratorType
import inspect
from pprint import pprint
from .helpers import (
  get_answer,
  Event,
  get_strs,
  get_tracer_kill_pack,
  filter_only,
)

def get_hmm():
  """Get a thought."""
  return 'hmmm...'

def hmm():
  """Contemplation..."""
  if get_answer():
    print(get_hmm())

class StopTracer(Exception):
  pass

counter0 = 0
def trace_hook_callback0(frame,event,arg):
  global counter0
  counter0 += 1
  if counter0 >= 5:
    sys.settrace(None)
    return None
  return

counter1 = 0
def trace_hook_callback1(frame,event,arg):
  """used in tester.stop_trace1
      stops when counter hits 10
  """
  global counter1
  counter1 += 1
  pkd_frm_strs = get_strs(frame,counter1)
  tkp = get_tracer_kill_pack()
  t = sys.gettrace()
  if counter1 >= 10:
    sys.settrace(None)
    raise StopTracer
  return

counter2 = 0
def trace_hook_callback2(frame,event,arg):
  """used in tester.stop_trace1
      stops when counter hits 10
  """
  global counter2, modules2
  evt = Event(frame,event,arg,collect_data='module')
  if not filter_only(evt.module,['hdlogger','tester']): return
  counter2 += 1
  if event == 'kill':
    sys.settrace(None)
    with open('_trace2.log','a') as f:
      f.write(f"{evt.data}")
      return evt.data
  return trace_hook_callback2

def thcb_evt0(frame,event,arg):
  evt = Event(frame,event,arg,
    collect_data='module')
  if not filter_only(evt.module,['hdlogger','tester']): return
  if event == 'kill':
    sys.settrace(None)
    with open('_thcb_evt0.log','a') as f:
      f.write(f"{evt.data}")
    return 'killed_evt0'
  return thcb_evt0

def thcb_evt1(frame,event,arg):
  """added write_data method to Event"""
  evt = Event(frame,event,arg,
    collect_data='module')
  if not filter_only(evt.module,['hdlogger','tester']): return
  if event == 'kill':
    sys.settrace(None)
    return evt.write_data()
  return thcb_evt1

def thcb_gen0(frame,event,arg):
  evt = Event(frame,event,arg,
    collect_data='module')
  if not filter_only(evt.module,['hdlogger','tester']): return
  if event == 'kill':
    sys.settrace(None)
    return 'killed_gen0'
  return thcb_gen0

def thcb_gen1(frame,event,arg):
  """added write_data method to Event"""
  evt = Event(frame,event,arg,
    write_flag=True,
    collect_data=False)
  if not filter_only(evt.module,['hdlogger','tester']): return
  if event == 'kill':
    sys.settrace(None)
    return evt.write_trace()
  return thcb_gen1

def local_call(frame,event,arg):
  print(1)

def local_line(frame,event,arg):
  print(2)

def local_ret(frame,event,arg):
  print(3)

def local_exc(frame,event,arg):
  print(4)

def local_op(frame,event,arg):
  print(5)

counter3 = 0
def thcb_gen2(frame,event,arg):
  global counter3
  print(f"in tracefunc: {counter3=}, {event=}, {arg=}")
  counter3 += 1
  if counter3 >= 10:
    sys.settrace(None)
    return
  if event == 'call':
    # global trace
    print('call',f"{arg=}")
    return thcb_gen2
  elif event == 'line':
    # local trace, arg=None, returns local trace func
    print('line',f"{arg=}")
    return local_line
  elif event == 'return':
    # local trace, returns ignored
    print('return',f"{arg=}")
    return local_ret
  elif event == 'exception':
    # local trace, arg=tuple(exception,value,tb),returns new local trace func
    print('exception',f"{arg=}")
    return local_exc
  elif event == 'opcode':
    # local trace, arg=None,returns new local trace func
    print('opcode',f"{arg=}")
    return local_op
  # if isinstance(arg,GeneratorType) or inspect.isgeneratorfunction(arg):
  #   arg,arg2 = tee(arg)
  #   evt = Event(frame,event,arg2,
  #     write_flag=True,
  #     collect_data='arg')
  print('c1')
  evt = Event(frame,event,arg,
    write_flag=True,
    collect_data=False)
  print('c2')
  if not filter_only(evt.module,['tester']): return
  print('c4')
  if event == 'kill':
    print('c5')
    sys.settrace(None)
    print('c6')
    return
  return thcb_gen2
