import pickle, sys, inspect
import pandas as pd
import pdir, stackprinter
from hdlogger.utils import *
from functools import cached_property
from collections import defaultdict
from pathlib import Path
from string import Template
from ipdb import set_trace as st

columns = [
  'frame',
  'event',
  'arg',
  'locals',
  'index',
  'function',
  'module',
  'filename',
  'lineno',
  'stdlib',
  'source',
  'format_filename'
]

class TraceProcessor:
  def __init__(self,filepath):
    self.pickleable_states = []
    self._dataframe = None
    self.initialize(filepath)

  def initialize(self,filepath):
    self.pickleable_states = []
    path = Path(filepath)
    lines = rf(path,"r")
    for line in lines:
      _as_hex,_as_bytes = line,bytes.fromhex(line)
      try:
        pickleable_state = pickle.loads(_as_bytes)
      except:
        sys.settrace(None)
        wf(stackprinter.format(sys.exc_info()),'logs/pickle.loads.log','a')
        from ipdb import set_trace as st; st()
        raise SystemExit(f"{line}")
      self.pickleable_states.append(pickleable_state)

  @property
  def dataframe(self):
    if self._dataframe: return self._dataframe
    data = defaultdict(lambda: list())
    for state in self.pickleable_states:
      for k,v in state.__dict__.items():
        data[k].append(v)
    self._dataframe = pd.DataFrame(data)
    return self._dataframe

filepath = '/Users/alberthan/VSCodeProjects/HDLogger/youtube-dl/logs/03.pickled_states_hex.tracer.log'
tp = TraceProcessor(filepath)
df = tp.dataframe
error_index = 1319
