import pickle, sys
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
# # manual
# path = Path(filepath)
# lines = rf(path,"r")
# pickleable_states = []
# data = defaultdict(lambda: list())
# for line in lines:
#   print(f"{line=}")
#   _as_hex, _as_bytes = line, bytes.fromhex(line)
#   try:
#     pickleable_state = pickle.loads(_as_bytes)
#   except:
#     sys.settrace(None)
#     wf(stackprinter.format(sys.exc_info()),'logs/pickle.loads.log','a')
#     from ipdb import set_trace as st; st()
#     raise SystemExit(f"{line}")
#   pickleable_states.append(pickleable_state)
#   for k,v in pickleable_state:
#     data[k].append(v)
# df = pd.DataFrame(data)

# end manual


# class TraceFormatter:
#   def __init__(self, dataframe, config):
#     self.dataframe = dataframe
#     self.rowtuples = dataframe.itertuples(name='Row')
#     self.columns = list(config.keys())
#     self.applyfuncs = list(config.values())
#     self.fmtdlines = []
#     TraceFormatter.format_dispatch()

#   @classmethod
#   def format_dispatch(cls):
#     template = '${who} likes ${what}'
#     d = dict(who='tim', what='mit')
#     t = Template(template)
#     t.safe_substitute(d)
#     df['cat'] = df.agg(lambda x: f"{x['a']} WAT {x['b']}", axis=1)
#     for row in self.rowtuples:
#       (Index, frame, event, arg, locals, index, function, module,
#        filename, lineno, stdlib, source, filename) = list(row)
#       if event == "call":`
#         s = (`
#           f"{self.index}|{filename}:{lineno}|{event}|"
#           f"{indent}|=>|"
#           f"{line.rstrip()}|"
#         )
#       if event == "line":
#         pass
#       if event == "return":
#         pass
#       if event == "exception":
#         pass
#       s = (
#         f""
#         f""
#       )
#       self.fmtdlines.append(s)
#     return self.fmtdlines

#   @cached_property
#   def format_call(self):
#     PickleableState.stack.append(f"{self.module}.{self.function}")
#     self.formatter = StateFormatter(
#       self.index, self.format_filename, self.lineno,
#       self.event, "\u0020" * (len(PickleableState.stack)-1), "=>",
#       function=self.function, arg=self.locals)
#     return str(self.formatter)

#   @cached_property
#   def format_line(self):
#     self.formatter = StateFormatter(
#       self.index, self.format_filename, self.lineno,
#       self.event, "\u0020" * len(PickleableState.stack), "  ",
#       source=self.source)
#     return str(self.formatter)

#   @cached_property
#   def format_return(self):
#     self.formatter = StateFormatter(
#       self.index, self.format_filename, self.lineno,
#       self.event, "\u0020" * (len(PickleableState.stack)-1), "<=",
#       function=f"{self.function}: ", arg=self.arg)
#     if PickleableState.stack and PickleableState.stack[-1] == f"{self.module}.{self.function}":
#       PickleableState.stack.pop()
#     return str(self.formatter)

#   @cached_property
#   def format_exception(self):
#     self.formatter = StateFormatter(
#       self.index, self.format_filename, self.lineno,
#       self.event, "\u0020" * (len(PickleableState.stack)-1), " !",
#       function=f"{self.function}: ", arg=self.arg)
#     return str(self.formatter)
