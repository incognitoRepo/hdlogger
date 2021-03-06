import pickle, sys, inspect, prettyprinter, snoop
import pandas as pd
import pdir, stackprinter
from hdlogger.utils import *
from functools import cached_property
from collections import defaultdict
from pathlib import Path
from string import Template
from typing import Any, Dict, List
from hdlogger.serializers.classes import PickleableFrame, CallEvt, LineEvt, RetnEvt, ExcpEvt
from ipdb import set_trace as st


# TODO: just pysnoop this shit
def formatter1(df):
  l = []
  for row in df.itertuples():
    if row.event == 'call': evt = CallEvt(function=row.function,f_locals=row.f_locals,stack=row.stack)
    if row.event == 'line': evt = LineEvt(source=row.source,stack=row.stack)
    if row.event == 'return': evt = RetnEvt(function=row.function,arg=row.arg,stack=row.stack)
    if row.event == 'exception': evt = ExcpEvt(function=row.function,arg=row.arg,stack=row.stack)
    static_vars = [row.st_count, row.filename, row.lineno, row.event]
    l.append(evt.nonstatic_rightpad(static_vars))
  ljd = '\n'.join(l)
  return ljd

class TraceProcessor:
  """holds pickleable states"""
  def __init__(self,filepath,formatter=formatter1):
    self.pickleable_states = []
    self._dataframe = None
    self.formatter = formatter
    self.initialize(filepath)
    pickler = pickle._Pickler
    unpickler = pickle._Unpickler

  def initialize(self,filepath):
    self.pickleable_states = []
    path = Path(filepath)
    lines = rf(path,"r")
    for line in lines:
      _as_hex,_as_bytes = line,bytes.fromhex(line)
      try:
        pickleable_state = pickle.loads(_as_bytes)
      except:
        wf(stackprinter.format(sys.exc_info()),'logs/pickle.loads.log','a')
        raise
      self.pickleable_states.append(pickleable_state)

  def format0(self,Index:int,frame:PickleableFrame,event:str,arg:Any,f_locals:Dict,count:int,function:str,module:str,filename:str,lineno:int,stdlib:bool,source:str,stack:List[str]):
    s = (
      f"{Index} {frame} {event} {arg} {f_locals} {count} {function}"
      f"{module} {filename} {lineno} {stdlib} {source} {stack}"
    )
    return s

  def level(self, n):
    df = self._dataframe.copy()
    df2 = df[df.stacklen.apply(lambda cell: cell <= n)]
    s = self.formatter(df2)
    wf(s, f'logs/level{n}.log','a')
    return s

  @property
  def level_1(self):
    df = self._dataframe.copy()
    df2 = df[df.stacklen.apply(lambda cell: cell <= df['stacklen'].max())]
    try:
      s = self.formatter(df2)
    except:
      s = stackprinter.format(sys.exc_info())
      wf(s, f"logs/{__name__}.log",'a')
      raise
    return s

  @property
  def level1(self):
    df = self._dataframe.copy()
    df2 = df[df.stacklen.apply(lambda cell: cell <= 1)]
    try:
      s = self.formatter(df2)
    except:
      s = stackprinter.format(sys.exc_info())
      wf(s, f"logs/{__name__}.log",'a')
      raise
    return s

  @property
  def dataframe(self):
    if self._dataframe is not None:
      return self._dataframe
    data = defaultdict(lambda: list())
    for state in self.pickleable_states:
      for k,v in state.__dict__.items():
        data[k].append(v)
    self._dataframe = pd.DataFrame(data)
    self._dataframe['stacklen'] = self._dataframe['stack'].apply(lambda cell: len(cell))
    return self._dataframe

if __name__ == '__main__':
  filepath = '/Users/alberthan/VSCodeProjects/HDLogger/youtube-dl/logs/03.pickled_states_hex.tracer.log'
  tp = TraceProcessor(filepath)
  df = tp.dataframe
