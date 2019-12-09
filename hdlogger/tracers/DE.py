import pickle
import pandas as pd
import pdir
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

def rf(filepath, mode="r"):
  path = Path(filepath)
  with path.open(mode) as f:
    lines = f.readlines()
  return lines


class TraceProcessor:
  def __init__(self,filepath):
    self.pickleable_states = []
    self.pickled_states_as_hex = []
    self.pickled_states_as_bytes = []
    self._dataframe = None
    self.initialize(filepath)

  def initialize(self,filepath):
    path = Path(filepath)
    lines = rf(path,"r")
    for line in lines:
      _as_hex,_as_bytes = line,bytes.fromhex(line)
      self.pickled_states_as_hex.append(_as_hex)
      self.pickled_states_as_bytes.append(_as_bytes)
      self.pickleable_states.append(pickle.loads(_as_bytes))

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

class TraceFormatter:
  def __init__(self, dataframe, config):
    self.dataframe = dataframe
    self.rowtuples = dataframe.itertuples(name='Row')
    self.columns = list(config.keys())
    self.applyfuncs = list(config.values())
    self.fmtdlines = []
    TraceFormatter.format_dispatch()

  @classmethod
  def format_dispatch(cls):
    template = '${who} likes ${what}'
    d = dict(who='tim', what='mit')
    t = Template(template)
    t.safe_substitute(d)
    df['cat'] = df.agg(lambda x: f"{x['a']} WAT {x['b']}", axis=1)
    for row in self.rowtuples:
      (Index, frame, event, arg, locals, index, function, module,
       filename, lineno, stdlib, source, filename) = list(row)
      if event == "call":
        s = (
          f"{self.index}|{filename}:{lineno}|{event}|"
          f"{indent}|=>|"
          f"{line.rstrip()}|"
        )
      if event == "line":
        pass
      if event == "return":
        pass
      if event == "exception":
        pass
      s = (
        f""
        f""
      )
      self.fmtdlines.append(s)
    return self.fmtdlines

  @cached_property
  def format_call(self):
    PickleableState.stack.append(f"{self.module}.{self.function}")
    self.formatter = StateFormatter(
      self.index, self.format_filename, self.lineno,
      self.event, "\u0020" * (len(PickleableState.stack)-1), "=>",
      function=self.function, arg=self.locals)
    return str(self.formatter)

  @cached_property
  def format_line(self):
    self.formatter = StateFormatter(
      self.index, self.format_filename, self.lineno,
      self.event, "\u0020" * len(PickleableState.stack), "  ",
      source=self.source)
    return str(self.formatter)

  @cached_property
  def format_return(self):
    self.formatter = StateFormatter(
      self.index, self.format_filename, self.lineno,
      self.event, "\u0020" * (len(PickleableState.stack)-1), "<=",
      function=f"{self.function}: ", arg=self.arg)
    if PickleableState.stack and PickleableState.stack[-1] == f"{self.module}.{self.function}":
      PickleableState.stack.pop()
    return str(self.formatter)

  @cached_property
  def format_exception(self):
    self.formatter = StateFormatter(
      self.index, self.format_filename, self.lineno,
      self.event, "\u0020" * (len(PickleableState.stack)-1), " !",
      function=f"{self.function}: ", arg=self.arg)
    return str(self.formatter)





def test(x):
  print(f"{x=}\n{type(x)=}\n{pdir(x)=}")
  print(type(x))
  print()

df.apply(test,axis=1)
