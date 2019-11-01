# -*- coding: utf-8 -*-
# vscode-fold=1
import dis, sys, inspect
from linecache import getline
from ipdb import set_trace as st
from itertools import tee
from types import GeneratorType
import inspect, ctypes
from pygments import highlight
from pygments.lexers import Python3Lexer
from pygments.formatters import Terminal256Formatter
from pygments.styles import get_style_by_name
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
  evt = Event(frame,event,arg,
    write_flag=True,
    collect_data=False)
  print("  \x1b[0;31mlocal_call\x1b[0m:",f"{arg=}")
  rf1,rf2,rf3 = thcb_gen2,local_call,None
  return rf1

def local_line(frame,event,arg):
  # Event here: arg=something
  evt = Event(frame,event,arg,
      write_flag=False,
      collect_data=False)
  print("  \x1b[0;32mlocal_line\x1b[0m:",f"{arg=}")
  rf1,rf2,rf3 = thcb_gen2,local_line,None
  return rf1

def local_ret(frame,event,arg):
  # list(arg) works here if put first (aka b4 global)
  # doesnt matter whats returned here, returning nothing works too
  # print(list(arg)); print(list(frame.f_locals['rv']))
  d = frame.f_locals
  dks = d.keys()
  type_val_pairs = []
  for k in dks:
    print(f"{' '*11}d: {k}={d[k]}({type(d[k])})")
    if isinstance(d[k],GeneratorType):
      arg = list(d['rv'])
      d['rv'] = [elm for elm in arg]
      frame.f_globals['rv'] = arg
      frame.f_locals.update({
          'rv': [elm for elm in arg],
      })
      ctypes.pythonapi.PyFrame_LocalsToFast(
          ctypes.py_object(frame), ctypes.c_int(0))
      print(f"{' '*5}    arg: {arg}")
      # frame.f_locals['rv2'] = [elm for elm in rvl]
      # del frame.f_locals['rv']
      # frame.f_locals['rv'] = frame.f_locals['rv2']
      # print(frame.f_locals['rv2'])
      # print(list(frame.f_locals['rv']))
      print(f"{' '*5} locals: {list(frame.f_locals['rv'])}")
      print(f"{' '*5}globals: {frame.f_globals['rv']}")
      # print(frame.f_locals['rv'])
  # evt = Event(frame,event,[elm for elm in arg],
  #     write_flag=True,
  #     collect_data=False)
  print("   \x1b[0;33mlocal_ret\x1b[0m:",f"{arg=}")
  rf1,rf2,rf3 = thcb_gen2,local_ret,None
  # return

def local_exc(frame,event,arg):
  print("  \x1b[1;34mlocal_exc\x1b[0m",f"{arg=}")
  rf1,rf2,rf3 = thcb_gen2,local_exc,None
  return rf1

def local_op(frame,event,arg):
  print("  \x1b[1;35mlocal_op\x1b[0m",f"{arg=}")
  rf1,rf2,rf3 = thcb_gen2,local_op,None
  return rf1

counter3a = 0
def thcb_gen2a(frame,event,arg):
  global counter3a
  src = getline(frame.f_code.co_filename,frame.f_lineno,frame.f_globals)
  srchld = highlight(src,Python3Lexer(),Terminal256Formatter(style=get_style_by_name('monokai')))
  this_func = "\x1b[2;3;96mthcb_gen2\x1b[0m"
  print(f"in {this_func}: {counter3a=}, {event=}, {arg=}")
  print(f"            : {frame.f_lineno:<03} {srchld}",end="")
  counter3a += 1
  if counter3a >= 10:
    sys.settrace(None)
    return
  if event == 'call':
    # global trace
    print("  \x1b[1;31mc\x1b[0m",f"{arg=}")
    # return local_call
  elif event == 'line':
    # local trace, arg=None, returns local trace func
    print("  \x1b[1;32ml\x1b[0m",f"{arg=}")
    # print(local_line(frame,event,arg))
    return local_line
  elif event == 'return':
    # local trace, returns ignored
    print("  \x1b[1;33mr\x1b[0m",f"{arg=}")
    return local_ret
  elif event == 'exception':
    # local trace, arg=tuple(exception,value,tb),returns new local trace func
    print("  \x1b[1;34me\x1b[0m",f"{arg=}")
    return local_exc
  elif event == 'opcode':
    # local trace, arg=None,returns new local trace func
    print("  \x1b[1;35mo\x1b[0m",f"{arg=}")
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

counter3 = 0
def thcb_gen2(frame,event,arg):
  global counter3
  src = getline(frame.f_code.co_filename,frame.f_lineno,frame.f_globals)
  srchld = highlight(src,Python3Lexer(),Terminal256Formatter(style=get_style_by_name('monokai')))
  this_func = "\x1b[2;3;96mthcb_gen2\x1b[0m"
  this_loco = "\x1b[2;3;97m   locals\x1b[0m"
  idt = " " * 12
  print(f"\nin {this_func}: {counter3=}, {event=}, {arg=}")
  print(f"   {this_loco}: {frame.f_locals.keys()}")
  print(f"{idt[:-4]}{frame.f_lineno:>4}: {srchld}",end="")
  counter3 += 1
  # if counter3 >= 10:
  #   sys.settrace(None)
  #   return
  module = frame.f_globals.get('__name__','')
  if not filter_only(module,['hdlogger','tester']):
    sys.settrace(None)
    return
  if event == 'call':
    # global trace
    print(f"{idt[:-1]}\x1b[1;31mc\x1b[0m: {arg=}")
    # return thcb_gen2 : local_line for every line event, except last
    # return local_call: local_line for return event and line event b4 return event
    # return None      : no local_line
    # no return        : no local_line
    # no return + return thcb_gen2 : l_l for every line event, except last
    local_call(frame,event,arg)
    return thcb_gen2
  elif event == 'return':
    return
    # local trace, returns ignored
    # doesn't matter what is returned here, but should return to stop global
    # list(arg) works here, if put first (aka b4 local)
    # print(list(arg))
    print(f"{idt[:-1]}\x1b[1;33mr\x1b[0m: {arg=}")
    local_ret(frame,event,arg)
    return
  elif event == 'line':
    # local trace, arg=None, returns local trace func
    # Event here: arg = None
    print(f"{idt[:-1]}\x1b[1;32ml\x1b[0m: {arg=}")
    # local_line(frame,event,arg)
    return local_line
  elif event == 'exception':
    # local trace, arg=tuple(exception,value,tb),returns new local trace func
    print(f"{idt[:-1]}\x1b[1;34me\x1b[0m: {arg=}")
    evt = Event(frame,event,arg,
      write_flag=True,
      collect_data=False)
    return local_exc
  elif event == 'opcode':
    # local trace, arg=None,returns new local trace func
    print(f"{idt[:-1]}\x1b[1;35mo\x1b[0m: {arg=}")
    evt = Event(frame,event,arg,
      write_flag=True,
      collect_data=False)
    return local_op
  evt = Event(frame,event,arg,
    write_flag=True,
    collect_data=False)
  print('c1 ',end="")
  print('c2 ')
  # return thcb_gen2

