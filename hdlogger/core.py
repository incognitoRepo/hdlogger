# -*- coding: utf-8 -*-
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
  logging.debug(f"{frame}\nf{event}\nf{arg}\n")
  return
