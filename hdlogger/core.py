# -*- coding: utf-8 -*-
import dis, sys, inspect
from pprint import pprint
import logging
from .helpers import (
  get_answer
)

# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

logging.basicConfig(
  filename="example.log",
  format="%(levelname)s:%(message)s",
  level=logging.DEBUG
  )
logging.debug("This message should go to the log file")

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
  print(f"\n{'=='*40}")
  print(f"{counter0=}\n")
  print(f"{event=}\n{arg=}\n")
  t = sys.gettrace()
  f = inspect.currentframe()
  e = 'kill'
  a = None
  with open('asdf','w') as f:
    f.write(str(counter0))
  if counter0 >= 5:
    sys.settrace(None)
  print(f"{frame=}\n")
  print(f"{frame.f_code=}\n")
  print(f"{dis.code_info(frame.f_code)=}")
  fc = frame.f_code
  print(f"{dis.disassemble(fc)=}")
  for instr in dis.get_instructions(fc):
    print(f"{instr=}")
  for line in dis.findlinestarts(fc):
    print(f"{line=}")
  print(f"\n{'=='*40}")
  # logging.debug(f"{frame}\nf{event}\nf{arg}\n")
  return

counter1 = 0
def trace_hook_callback1(frame,event,arg):
  """used in tester.stop_trace1
      stops when counter hits 10
  """
  global counter1
  counter1 += 1
  print(f"\n{'=='*40}")
  print(f"{counter1=}\n")
  print(f"{event=}\n{arg=}\n")
  t = sys.gettrace()
  f = inspect.currentframe()
  e = 'kill'
  a = None
  with open('asdf','w') as f:
    f.write(str(counter1))
  if counter1 >= 10:
    sys.settrace(None)
  print(f"{frame=}\n")
  print(f"{frame.f_code=}\n")
  print(f"{dis.code_info(frame.f_code)=}")
  fc = frame.f_code
  print(f"{dis.disassemble(fc)=}")
  for instr in dis.get_instructions(fc):
    print(f"{instr=}")
  for line in dis.findlinestarts(fc):
    print(f"{line=}")
  print(f"\n{'=='*40}")
  return

counter2 = 0
def trace_hook_callback2(frame,event,arg):
  """used in tester.stop_trace1
      stops when counter hits 10
  """
  global counter2
  counter2 += 1
  fc = frame.f_code
  print(f"{counter2=}")
  # if counter2 >= 100:
  #   return sys.settrace(None)
  if event == 'kill':
    sys.settrace(None)
    return 'killed'
  return trace_hook_callback2


