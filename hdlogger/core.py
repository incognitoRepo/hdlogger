# -*- coding: utf-8 -*-
# vscode-fold=1
import dis, sys, inspect
from ipdb import set_trace as st
from itertools import tee
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

def thcb_gen2(frame,event,arg):
  if isinstance(arg,GeneratorType):
    arg,arg2 = tee(arg)
  evt = Event(frame,event,arg2,
    write_flag=True,
    collect_data='arg')
  if not filter_only(evt.module,['hdlogger','tester']): return
  if event == 'kill':
    sys.settrace(None)
    evt.write_data()
    return evt.write_trace()
  return thcb_gen1
