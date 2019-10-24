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

def trace_hook_callback(frame,event,arg):
  print(f"\n{'=='*40}")
  print(f"{event=}\n{arg=}\n")
  t = sys.gettrace()
  pprint(inspect.getmembers(t))
  f = inspect.currentframe()
  e = 'kill'
  a = None
  print(f"{t(f,e,a)}")
  if event == 'kill':
    raise SystemExit()
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
