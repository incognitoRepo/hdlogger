# -*- coding: utf-8 -*-
# vscode-fold=1
import dis, sys, inspect
from pprint import pprint
import logging
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
  evt = Event(frame,event,arg,collect_module_data=True)
  if not filter_only(evt.module,['hdlogger','tester']): return
  counter2 += 1
  # print(f"{counter2=}")
  # print(f"{evt.module}")
  if event == 'kill':
    sys.settrace(None)
    with open('zztrace2.log','a') as f:
      f.write(f"{', '.join([elm for elm in evt.module_data])}")
    print(evt.module_data)
    return evt.module_data
  return trace_hook_callback2

modules0 = set()
def thcb_evt0(f,e,a):
  global modules0
  evt = Event(f,e,a)
  if filter(evt.module): return
  # print(f"{evt.module=}")
  # print(f"{evt.filename=}")
  # print(f"{evt.stdlib=}")
  if e == 'kill':
    sys.settrace(None)
    with open('zzthcb_evt0.log','a') as f:
      f.write(f"{', '.join([elm for elm in modules0])}")
    return 'killed_evt0'
  return thcb_evt0
