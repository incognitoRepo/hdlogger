#// vscode-fold=1
"""
python imports
pwd = '/Users/alberthan/VSCodeProjects/vytd/src/youtube-dl/bin'
# adding the following should make the import work in any pwd
p = '/Users/alberthan/VSCodeProjects/vytd/src/youtube-dl/bin'
sys.path.append(p)
import fmtutil
"""
import hunter, re, os, types, sys, shelve, dbm, base64, yaml
from ruamel.yaml import YAML
import simplejson as json
import jsonpickle
from ast import literal_eval as leval
from itertools import count
from functools import singledispatchmethod, cached_property
from typing import List, Dict, Iterable, Union
from types import TracebackType, GeneratorType
from hunter import Q, Query, Event
from hunter.predicates import And, When
from hunter.actions import CallPrinter, CodePrinter, VarsPrinter, VarsSnooper, CALL_COLORS, MISSING
import io,threading
from collections import namedtuple, defaultdict, deque
from functools import partial
from fsplit.filesplit import FileSplit
from pathlib import Path
from tblib import Traceback
import pandas as pd
from copy import deepcopy
import pickle, inspect
import traceback, stackprinter
from enum import Enum
from pdb import set_trace as st
from dataclasses import dataclass, field, InitVar
from prettyprinter import cpprint, pprint, pformat
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import Terminal256Formatter
from prettyprinter import pprint
from urllib.parse import urlparse, ParseResult
from urllib.response import addinfourl
from pprint import pformat
from hunter.util import safe_repr
from youtube_dl.evt_loader import process_dcts, process_vs
from optparse import OptionParser
import copyreg

def pickle_traceback(tb):
  return "\n".join(traceback.format_tb(tb))

copyreg.pickle(TracebackType,pickle_traceback)
DEBUG = "dbg_cfg_ret.log"

def info(o):
  try:
    lng = len(o)
  except TypeError as exc:
    lng = "cannot len this obj"
  typ = type(o)
  s = f"\n\n{typ}, {lng}\n{repr(o)}\n\n"
  return s

def dict_prnt(d):
  key_lst = list(d.keys())
  key_lst2 = [k for k in key_lst if not (k.startswith('_') or k.startswith('__'))]
  new_dct = {k:d[k] for k in key_lst2}
  ns = pformat(new_dct)
  return ns

def is_io(obj):
  if isinstance(obj,io.StringIO) or isinstance(obj,io.BytesIO):
    return True
  return False

def auto_repr(obj):
  try:
    if isinstance(obj, addinfourl):
      def repr_io(v):
        return v.__class__.__name__ if isinstance(v,io.StringIO) or isinstance(v,io.BytesIO) else v
      _d = obj.__dict__hc
      d = {k:repr_io(v) for k,v in _d.items() if not (k.startswith('_'))}
      return d
    elif isinstance(obj, OptionParser):
      try:
        _ = obj.option_list
        def nodctrepr(v): return repr(v) if not isinstance(v,dict) else repr(v.keys())
        obj = [nodctrepr(elm) for elm in _]
      except:
        with open('hc91.log','a') as f:
          f.write("\n".join(arg))
        raise SystemExit
    class_name = obj.__class__.__name__
    part_1 = f'<{class_name}: '
    items = []
    _d = obj.__dict__
    d = {k:v for k,v in _d.items() if not (k.startswith('_'))}
    for k,v in d.items():
      try:
        if is_class(v): nv = auto_repr(v)
        elif isinstance(v,dict): nv = pformat(v)
        elif isinstance(v,io.StringIO) or isinstance(v,io.BytesIO):
          nv = v.__class__.__name__
        else: nv = repr(v)
        s = f'{k} = {nv}'
        items.append(s)
      except:
        with open('auto_repr.log','a') as f:
          f.write(f"{obj}")
        raise SystemExit
    secondary_indent = ' '*len(part_1)
    part_2 = f',{secondary_indent}'.join(items)
    return f'{part_1}{part_2}>'
  except AttributeError:
    with open('auto_repr_err.log','a') as f:
      f.write(stackprinter.format(sys.exc_info()))
    raise SystemExit

def is_class(obj):
  s = repr(obj)
  if s.startswith("<class"):
    return True
  return False

def is_instance(obj):
  rgx = re.compile(r"<(?P<module>[_A-z][A-z_0-9]*)[.](?P<klass>[A-z_][A-z_0-9]*)")
  m = rgx.match(repr(obj))
  if m:
    module,klass = m.groupdict().values()
    return module,klass
  return False

def has_dct(obj):
  # with open('has_d.log','w') as f:
    # f.write(str(vars()))
  if hasattr(obj,'_asdict'):
    d = obj._asdict()
  else:
    d = obj.__dict__
  return dict_prnt(d)

def is_function(obj):
  if str(obj).startswith("<function"):
    return auto_repr(obj)
  return False

def debug_error(obj, err_type, attempted_str="", **funcs):
  filename = "attribute" if err_type == "AttributeError" else "type"
  s = f"info: \n{info(obj)}"
  att = f"attempted str: \n{attempted_str}" if attempted_str else ""
  ar = f"auto_repr: \n{auto_repr(obj)}"
  lst = []
  for func in funcs:
    lst.append(repr(func(obj)))
  joined_lst = '\n'.join(lst)
  write_value = f"{s}\n{att}\n{ar}\n{joined_lst}"
  with open(f"{filename}_err.log","w") as f:
    f.write(write_value)
  print(write_value)

Supplement = namedtuple(
  'Supplement',
  'filename_prefix event_kind indent_len event_symbol event_function event_source h_idx')
SupplementalField = namedtuple(
  'SupplementalField',
  'mono poly')

@dataclass
class Color:
  color_modifiers = {
    'RESET': '\x1b[0m',
    'BRIGHT': '\x1b[1m',
    'DIM': '\x1b[2m',
    'NORMAL': '\x1b[22m',
  }
  segment_colors = {
    'CALL': '\x1b[1m\x1b[34m',
    'LINE': '\x1b[39m',
    'RETURN': '\x1b[1m\x1b[32m',
    'EXCEPTION': '\x1b[1m\x1b[31m',
    'COLON': '\x1b[1m\x1b[30m',
    'LINENO': '\x1b[0m',
    'KIND': '\x1b[36m',
    'CONT': '\x1b[1m\x1b[30m',
    'VARS': '\x1b[1m\x1b[35m',
    'VARS-NAME': '\x1b[22m\x1b[35m',
    'INTERNAL-FAILURE': '\x1b[1m\x1b[41m\x1b[31m',
    'INTERNAL-DETAIL': '\x1b[37m',
    'SOURCE-FAILURE': '\x1b[1m\x1b[43m\x1b[33m',
    'SOURCE-DETAIL': '\x1b[37m',
  }
  fg_colors = {
    'fore(BLACK)': '\x1b[30m',
    'fore(RED)': '\x1b[31m',
    'fore(GREEN)': '\x1b[32m',
    'fore(YELLOW)': '\x1b[33m',
    'fore(BLUE)': '\x1b[34m',
    'fore(MAGENTA)': '\x1b[35m',
    'fore(CYAN)': '\x1b[36m',
    'fore(WHITE)': '\x1b[37m',
    'fore(LIGHTBLACK_EX)': '\x1b[90m',
    'fore(LIGHTRED_EX)': '\x1b[91m',
    'fore(LIGHTGREEN_EX)': '\x1b[92m',
    'fore(LIGHTYELLOW_EX)': '\x1b[93m',
    'fore(LIGHTBLUE_EX)': '\x1b[94m',
    'fore(LIGHTMAGENTA_EX)': '\x1b[95m',
    'fore(LIGHTCYAN_EX)': '\x1b[96m',
    'fore(LIGHTWHITE_EX)': '\x1b[97m',
    'fore(RESET)': '\x1b[39m',
  }
  bg_colors = {
    'back(BLACK)': '\x1b[40m',
    'back(BLUE)': '\x1b[44m',
    'back(CYAN)': '\x1b[46m',
    'back(GREEN)': '\x1b[42m',
    'back(LIGHTBLACK_EX)': '\x1b[100m',
    'back(LIGHTBLUE_EX)': '\x1b[104m',
    'back(LIGHTCYAN_EX)': '\x1b[106m',
    'back(LIGHTGREEN_EX)': '\x1b[102m',
    'back(LIGHTMAGENTA_EX)': '\x1b[105m',
    'back(LIGHTRED_EX)': '\x1b[101m',
    'back(LIGHTWHITE_EX)': '\x1b[107m',
    'back(LIGHTYELLOW_EX)': '\x1b[103m',
    'back(MAGENTA)': '\x1b[45m',
    'back(RED)': '\x1b[41m',
    'back(RESET)': '\x1b[49m',
    'back(WHITE)': '\x1b[47m',
    'back(YELLOW)': '\x1b[43m'
  }

  def fore(self,txt,key=None):
    """..key: segment|color"""
    segment_keys = self.segment_colors.keys()
    if key in segment_keys:
      c = self.segment_colors[key]
    else:
      _key = f"fore({key})"
      c = self.fg_colors[_key]
    reset = self.color_modifiers['RESET']
    s = (
      f"{c}",
      f"{txt}",
      f"{reset}",
    )
    sj = "".join(s)
    return sj

  def color_test(self):
    for COLORS in [self.fg_colors,self.fg_colors]:
      d = {
        'dict': COLORS['__dict__'],
        'foredict': COLORS['fore(__dict__)'],
        'backdict': COLORS['back(__dict__)'],
      }
      ocs = {k:v for k,v in COLORS.items() if not "__" in k}
      for k,v in COLORS.items():
        print(f"{k}: {v}")
      for k,v in COLORS.items():
        print(f'"{k}": "{repr(v)}"')
      for k,v in d.items():
        print(f"{k}: {v}")
      for k,v in d.items():
        print(f'"{k}": "{repr(v)}"')

@dataclass
class EventKind:
  event: InitVar
  event_kind: str = field(init=False)
  event_function: str = field(init=False)
  filename_prefix_mono: str
  filename_prefix_poly: str
  stack: int
  fmtdstr: str = ""
  argvars: Dict = field(default_factory=dict)
  color: Color = Color()

  def get_argvars(self,event):
    """event.arg from sys.settrace(tracefunc)
    ..call: `None`
    ..line: `None`
    ..return: `retval` or `None` (if exc)
    ..exception: `(exception, value, traceback)`
               : `(type, value, traceback)`
               : `(exception_class, instance, traceback)`
    """
    raise NotImplementedError("setup the dispatch")

  def __post_init__(self, event):
    d = {'call': self.get_argvars, 'line': lambda e: e.fullsource,
    'return': self.get_argvars, 'exception': self.get_argvars}
    self.event_kind = event.kind
    self.event_function = str(event.function)
    self.argvars = d[event.kind](event)

@dataclass
class CallEvent(EventKind):
  symbol: str = "=>"
  separator: str = "   "
  _first:str = ""
  _rest: str = ""

  def get_argvars(self,event) -> Dict:
    varnames = event.code.co_varnames
    argcount = event.code.co_argcount
    d = {}
    for var in varnames:
      val = str(event.locals.get(var))
      d = {var:val}
    return d

  def fmtd_str(self,c=False,prefix_symbol=""):
    psym = prefix_symbol
    ms1 = (
        f"{self.filename_prefix_mono}{self.event_kind:9} "
        f"{self.separator * (len(self.stack) - 1)}{self.symbol} "
        f"{self.event_function}"
    )
    lms1 = len(ms1)+len("(")
    join_mstr = f",\n{' '*lms1}"
    mavs = (
        f"({join_mstr.join([f'{k}={v}' for k,v in self.argvars.items()])})"
    )
    if self._first and self._rest:
      first,rest = self._first,self._rest
    else:
      first,*rest = mavs.split('\n',1)
      self._first,self._rest = first,rest
    ms = f"{psym}{ms1}{mavs}"
    if c:
      aac = argvars_argname_color = "MAGENTA"
      ps1 = (
          f"{self.filename_prefix_poly}{self.color.fore(f'{self.event_kind:9}','KIND')} "
          f"{self.separator * (len(self.stack) - 1)}{self.color.fore(self.symbol,'CALL')} "
          f"{self.event_function}"
      )
      lps1 = lms1
      join_pstr = f",\n{' '*lps1}"
      pavs = (
        f"({join_pstr.join([f'{self.color.fore(k,aac)}={v}' for k,v in self.argvars.items()])})"
      )
      ps = f"{psym}{ps1}{pavs}"
      return ps
    return ms

  def __str__(self):
    if not self.fmtdstr:
      self.fmtdstr = self.fmtd_str()
      return self.fmtdstr
    else:
      return self.fmtdstr

@dataclass
class ExceptionEvent(EventKind):
  symbol: str = " !"
  separator: str = "   "

  def get_argvars(self,event) -> Dict:
    """event.arg from sys.settrace(tracefunc)
    ..exception: `(exception, value, traceback)`
               : `(type, value, traceback)`
               : `(exception_class, instance, traceback)` # this is tb.print_tb() str
    """
    assert isinstance(event.arg,dict), type(event.arg)
    assert len(event.arg) == 3, f"{type(event.arg)=}, {len(event.arg)=}\n{event.arg=}"
    # event.arg.keys() ["exception","value","traceback"]
    return event.arg

  def fmtd_str(self,c=False,prefix_symbol=""):
    psym = prefix_symbol
    ms1 = (
        f"{self.filename_prefix_mono}{self.event_kind:9} "
        f"{self.separator * (len(self.stack) - 1)}{self.symbol} "
        f"{self.event_function}"
    )
    lms1 = len(ms1)+len("(")
    join_mstr = f",\n{'+'*lms1}"
    mavs = (
        f"({join_mstr.join(traceback.format_exception_only(self.argvars['exception'],self.argvars['value'])).strip()})"
    )
    ms = f"{psym}{ms1}{mavs}"
    if c:
      aac = argvars_argname_color = "MAGENTA"
      ps1 = (
          f"{self.filename_prefix_poly}{self.color.fore(f'{self.event_kind:9}','KIND')} "
          f"{self.separator * (len(self.stack) - 1)}{self.color.fore(self.symbol,'EXCEPTION')} "
          f"{self.event_function}"
      )
      lps1 = lms1
      join_pstr = f",\n{' '*lps1}"
      pavs = (
        f"({join_pstr.join(traceback.format_exception_only(self.argvars['exception'],self.argvars['value'])).strip()})"
      )
      ps = f"{psym}{ps1}{pavs}"
      return ps
    return ms

  def __str__(self):
    if not self.fmtdstr:
      self.fmtdstr = self.fmtd_str()
      return self.fmtdstr
    else:
      return self.fmtdstr

@dataclass
class ReturnEvent(EventKind):
  symbol: str = "<="
  separator: str = "   "
  debug: bool = True

  def get_argvars(self,event) -> Dict:
    """event.arg from sys.settrace(tracefunc)
    ..return: `retval` or `None` (if exc)
    """
    if not event.arg:
      d = {"retval":"None"}
    elif isinstance(event.arg,str):
      d = {"retval": [repr(event.arg)]}
    elif isinstance(event.arg,Iterable):
      if isinstance(event.arg,Dict):
        d = {k:[repr(v)] for k,v in event.arg.items()}
      elif isinstance(event.arg,List):
        d = self.argvars = {"retval": [repr(elm) for elm in event.arg]}
      else:
        d = {'retval': event.arg}
    else:
      d = {"retval":["else_error"]}
    return d

  def implies_iterable_is_str_len1(self,v):
    if (v[0] in ("{","[","(")
        and isinstance(v[0],str)
        and len(v) > 1
        and len(v[0]) == 1):
      return True
    else:
      return False

  def fmtd_str(self,c=False,prefix_symbol=""):
    typ = lambda o: type(o).__name__

    def is_url(url):
      try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
      except ValueError:
        return False

    psym = prefix_symbol
    j = lambda lst: "\n".join(lst)
    rm_rq = lambda s: s.replace("'","") # remove redundant quotes
    vl = list(self.argvars.values())[0]
    ts,ts0 = set(),set()
    if not vl or vl == "None": return "()"
    vl = [rm_rq(elm).strip() for elm in vl]
    rest, restl = "",[]
    ms1 = (
        f"{self.filename_prefix_mono}{self.event_kind:9} "
        f"{self.separator * (len(self.stack) - 1)}{self.symbol} "
        f"{self.event_function}"
    )
    lms1 = len(ms1.strip())+1 # fmt:375 strip is opt
    def get_lms1(newline,debug_separator):
      nl = "\n" if newline else ""
      sep = ' ' if not self.debug else debug_separator
      s = f"{nl}{sep*lms1}"
      return s
    join_mstr = f",\n{' '*lms1}"
    assert isinstance(join_mstr,str), join_mstr
    ms2 = f"{self.event_function}"


    vlst = []
    first = True
    for k,v in self.argvars.items():
      l = v
      fv = None
      assert isinstance(l,list), f"{l=}"
      l0 = l[0]
      if isinstance(l0,str) and l0.lower() in ('true','false'): # bool
        if l0.lower() == 'true':
          fv = True
        else:
          fv = False
      elif len(l) > 10:
        fv = l
      elif isinstance(l0,list):
        fv = eval(l0)
      elif "," not in l0: # not container
        if l0.isnumeric():
          fv = int(l0)
        elif is_url(l0):
          fv = urlparse(l0).geturl()
        elif isinstance(l0,ParseResult):
          fv = urlparse(l0).geturl()
        elif not l0:
          fv = "()"
        else:
          fv = l0
      else:
        try:
          fv = eval(l0)
        except:
          fv = l0

      if isinstance(fv,list) and isinstance(fv[0],str) and (len(fv) > 5):
        pfv = ""
        f_flag = True
        for elm in fv:
          if f_flag:
            pfv += elm
            f_flag = False
          else:
            pfv += get_lms1(False,'1') + elm
      elif isinstance(fv,list):
        l = []
        pfv = ""
        f_flag = True
        if isinstance(fv[0],dict):
          d = fv[0]
          for vk,vv in d.items():
            if f_flag:
              itm = get_lms1(False,'2') + vk + ": " + str(vv)
              l.append(itm)
            else:
              itm = get_lms1(False,'3') + vk + ": " + str(vv)
              l.append(itm)
          pfv =  "\n".join(l)
        else:
          pfv = get_lms1(True,'4') + k + ": " + str(fv)

      elif isinstance(fv,dict):
        splt = pformat(fv).split('\n')
        pfv = ""
        for line in splt:
          if first:
            pfv = k + ": " + str(fv)
            first = False
          else:
            pfv += get_lms1(True,'5') + k + ": " + line
      else:
        if isinstance(fv,bool) or isinstance(fv,int):
          if first:
            pfv = k + ": " + str(fv)
            first = False
          else:
            pfv = get_lms1(False,'6') + k + ": " + str(fv)
        else:
          if first:
            pfv = k + ": " + pformat(fv)
            first = False
          else:
            pfv = get_lms1(False,'7') + k + ": " + pformat(fv)
      vlst.append(pfv)
    mavs = "\n".join(vlst)
    mavs = "(" + mavs + ")"


    restj = f"{ms1}{mavs}"
    ms = f"{psym}{restj}"
    if c:
      return ms
    return ms

  def __str__(self):
    if not self.fmtdstr:
      self.fmtdstr = self.fmtd_str()
      return self.fmtdstr
    else:
      return self.fmtdstr

@dataclass
class LineEvent(EventKind):
  symbol: str = "<="
  separator: str = "   "

  def get_argvars(self, event) -> Dict:
    sauce = str(event.fullsource)
    sauce = sauce.strip()
    d = {"line_source":[sauce]}
    return d

  def fmtd_str(self,c=False,prefix_symbol=""):
    """this is ugly code. i moved the fmt_syms into these classes bc
    i needed the secondary idt, but for line events, there are never
    secondary idts (these multiline rows are for verbose argvars)
    otoh, line events have a unique feature that they use the 1st line as a
    header line, so the sym is different and there is a scondary idt for adjacent.
    if this works, i will keep it like this until i can get a mvp."""
    psym = prefix_symbol
    ms1 = (
        f"{self.filename_prefix_mono}{self.event_kind:9} "
        f"{self.separator * len(self.stack)} "
    )
    lms1 = len(ms1)+len("(")
    join_mstr = f",\n{' '*lms1}"
    mavs = (
        f"{self.argvars}"
    )
    ms = f"{psym}{ms1}{mavs}"
    if c:
      aac = argvars_argname_color = "MAGENTA"
      ps1 = (
          f"{self.filename_prefix_poly}{self.color.fore(f'{self.event_kind:9}','KIND')} "
          f"{self.separator * len(self.stack)} "
      )
      lps1 = lms1
      join_pstr = f",\n{' '*lps1}"
      pavs = (
        f"{self.argvars}"
      )
      ps = f"{psym}{ps1}{pavs}"
      return ps
    return ms

  def __str__(self):
    if not self.fmtdstr:
      self.fmtdstr = self.fmtd_str()
      return self.fmtdstr
    else:
      return self.fmtdstr

class CustomPrinter(CallPrinter):
  EVENT_COLORS = CALL_COLORS

  def __init__(self, base_path, *args, **kwargs):
    super(CustomPrinter, self).__init__(*args, **kwargs)
    self.locals = defaultdict(list)
    self.count = count(0)
    self.base_path = base_path
    self.pickle_path = base_path.joinpath('pickle')
    self.shelf_path = base_path.joinpath('shelf')
    self.yaml_path = base_path.joinpath('yaml')
    self.json_path = base_path.joinpath('json')
    self.debugfilepth = Path('/Users/alberthan/VSCodeProjects/vytd/src/youtube-dl/bin/debug.log')
    self.pklcnt = count()
    self.clrs = Color().fore
    # self.old_fn = ""

  def write_to_debugfile(self,f,f2,f3,frv):
    s = (
      f"f: {f}",
      f"f2: {f2}",
      f"f3: {f3}",
      f"frv: {frv}",
    )
    sj = "\n".join(s)
    with open(self.debugfilepth,'a') as f:
      f.write(sj+"\n\n")

  def filename_prefix(self, event=None, count=None):
    FilenamePrefix = namedtuple('FilenamePrefix', 'mono poly')
    og_index = f"{count:0>5}"
    if event:
      filename = Path(event.filename) or '<???>'
      if filename.stem == "init":
        filename2 = f"{filename.parent.stem[0]}{filename.stem}"
      else:
        filename2 = f"{filename.stem}"
      filename3 = filename2[:self.filename_alignment]

      ms = (
        f"{filename3:_>{self.filename_alignment}}:"
        f"({event.lineno:0>5}|{og_index})"
      )
      ps = (
        f"{filename3:_>{self.filename_alignment}}{self.other_colors['COLON']}:"
        f"({self.other_colors['LINENO']}{event.lineno:0>5}|{og_index})"
      )
      filename_prefix = FilenamePrefix(ms,ps)
      return filename_prefix
    else:
      print('error in filename_prefix')
      st()
      assert 1/0, 'wtf'

  def output_format(self, format_str, *args, **kwargs):
    output = (format_str.format(
      *args,
      **dict(self.other_colors, **kwargs)
    ))
    return output

  def write_output(self,outstr):
      self.stream.write(outstr)

  def get_locals(self,event,var):
    if event.detached:
      return event.locals.get(var, MISSING)
    else:
      return self.try_repr(event.locals.get(var, MISSING))

  def get_evt_dcts(self):
    self_id = id(self)
    return self.evt_dcts

  def event_dict(self,e,count):
    """e: event"""
    d = {
    'arg':e.arg,
    'calls':e.calls,
    'count':count,
    # 'code':e.code,
    'depth':e.depth,
    # 'detach':e.detach,
    # 'detached':e.detached,
    'filename':e.filename,
    # 'frame':frame,
    'fullsource':e.fullsource,
    'function':e.function,
    # 'function_object':e.function_object,
    # 'globals':frame['f_globals'],
    'kind':e.kind,
    'lineno':e.lineno,
    # 'locals':e.locals,
    'module':e.module,
    # 'source':e.source
    }
    return d

  def update_evt_dct_1(self,evt_dct,event,filename_prefix_mono,filename_prefix_poly,stack,output):
    d = {'call': CallEvent, 'line': LineEvent,
    'return': ReturnEvent, 'exception': ExceptionEvent}
    hntr_evt = d[event.kind](event,filename_prefix_mono,filename_prefix_poly,stack)
    evt_dct['hunter_event'] = hntr_evt
    evt_dct['hunter_monostr'] = hntr_evt.fmtd_str(c=False)
    evt_dct['hunter_polystr'] = hntr_evt.fmtd_str(c=True)
    evt_dct['hunter_raw_output'] = output
    return evt_dct

  def event_detach(self,og_event,d=None):
    event = Event.__new__(Event)

    event.__dict__['code'] = og_event.code
    event.__dict__['filename'] = og_event.filename
    event.__dict__['fullsource'] = og_event.fullsource
    event.__dict__['function'] = og_event.function
    event.__dict__['lineno'] = og_event.lineno
    event.__dict__['module'] = og_event.module
    event.__dict__['source'] = og_event.source
    event.__dict__['stdlib'] = og_event.stdlib
    event.__dict__['threadid'] = og_event.threadid
    event.__dict__['threadname'] = og_event.threadname

    if d:
      keys = list(d.keys())
      if 'arg' in keys:
        event.__dict__['arg'] = d['arg'](og_event.arg)
      else:
        event.__dict__['arg'] = {}
      if 'globals' in keys:
        event.__dict__['globals'] = {key: d['globals'](value) for key, value in og_event.globals.items()}
      else:
        event.__dict__['globals'] = {}
      if 'locals' in keys:
        event.__dict__['locals'] = {key: d['locals'](value) for key, value in og_event.locals.items()}
      else:
        event.__dict__['locals'] = None

    else:
      event.__dict__['globals'] = {}
      event.__dict__['locals'] = {}
      event.__dict__['arg'] = None

    event.threading_support = og_event.threading_support
    event.calls = og_event.calls
    event.depth = og_event.depth
    event.kind = og_event.kind
    event.detached = True
    return event

  def process_event_arg_BAK(self,a):
    if isinstance(a,tuple) and isinstance(a[1],BaseException):
      d = {
        'exception': deepcopy(a[0]),
        'value': deepcopy(a[1]),
        'traceback': traceback.format_tb(a[2])
      }
      return d
    elif isinstance(a,dict):
      d = {}
      for k,v in a.items():
        if isinstance(v,dict):
          nv = {vk:str(vv) for vk,vv in v.items()}
        else:
          nv = str(v)
        d.update({k:nv})
      return d
    elif isinstance(a,list):
      l = []
      for elm in a:
        if isinstance(elm,str):
          l.append(elm)
        else:
          l.append(repr(elm))
      return l
    else:
      return repr(a)

  def process_event_arg2(self,a):
    if not a:
      return
    if str(a).startswith("<Values"):
      lod = [a.__dict__]
      prcsd = process_dcts(lod)
    if isinstance(a,dict) and (
      isinstance(list(a.values())[0],dict)):
      lod = list(a.values())
      prcsd = process_dcts(lod)
    if not isinstance(a,list) or isinstance(a,tuple):
      if not isinstance(a,dict):
        d = {'process_event_arg':a}
        lod = [d]
        prcsd = process_dcts(lod)
      else:
        lod = [a]
        prcsd = process_dcts(lod)
    else:
      prcsd = process_vs(a)
    return prcsd

  def process_event_arg(self,a):
    try:
      if not a: return
      prcsd = process_dcts([{'prcsd':a}])
      return prcsd
    except:
      with open('hc798','a') as f:
        f.write(info(a))

  def read_from_pickle(self):
    """Load each item that was previously written to disk."""
    pkld_strhex = Path(self.pickle_path).parent.joinpath('eventpickle_hex')
    with open(pkld_strhex, 'r') as file:
      try:
        lines = file.readlines()
        decoded_lines = [bytes.fromhex(elm) for elm in lines]
        unpkld_lines = [pickle.loads(elm) for elm in decoded_lines]
        return unpkld_lines
      except EOFError as err:
        with open('hc804','a') as f:
          f.write(stackprinter.format(err))

  def write_to_pickle(self,arg,h_idx=0):
    Pkl = namedtuple('Pkl', 'arg type h_idx')
    pre_pkld = ""
    lvl1sep = f"\n{'-'*80}\n"
    lvl2sep = f"\n  {'-'*60}\n  "

    def main(arg) -> bool:
      try:
        if not arg or arg == None:
          pkld = Pkl(pickle.dumps(arg),pickle.dumps(None),h_idx)
          return_value = write_to_disk(pkld,debug=True)
          return return_value
        og_arg = arg
        # cleaned_arg = make_event_arg_pickleable(arg)
        pkld = get_pickled_bytes(arg,h_idx)
        return_value = write_to_disk(pkld,og_arg,debug=True)
        return return_value
      except:
        with open('hc843.log','a') as f:
          f.write(stackprinter.format())
          f.write(f"\n{arg}")
        raise SystemExit

    def make_event_arg_pickleable(arg,keep=False):
      if isinstance(arg,tuple) and isinstance(arg[1],BaseException):
        assert arg[2] is None or isinstance(arg[2],TracebackType), f"{info(arg)}"
        try:
          arg = traceback.format_exception_only(arg[0],arg[1])
        except:
          return arg
      elif isinstance(arg,addinfourl):
        arg = auto_repr(arg)
      elif isinstance(arg,OptionParser):
        try:
          _ = arg.option_list
          def nodctrepr(v): return repr(v) if not isinstance(v,dict) else repr(v.keys())
          arg = [nodctrepr(elm) for elm in _]
        except:
          with open('hc860.log','a') as f:
            f.write("\n".join(arg))
          raise SystemExit
      else:
        arg = arg
      return arg

    def get_pickled_bytes(cleaned_arg,h_idx):
      arg = cleaned_arg
      try:
        pre_pkld = Pkl(pickle.dumps(arg), type(arg), h_idx)
        return pre_pkld
      except pickle.PickleError as err:
        if isinstance(arg,tuple) and isinstance(arg[1],BaseException):
          assert arg[2] is None or isinstance(arg[2],TracebackType), f"{info(arg)}"
          try:
            arg = traceback.format_exception_only(arg[0],arg[1])
          except:
            return arg
        elif isinstance(arg,addinfourl):
          arg = auto_repr(arg)
        elif isinstance(arg,OptionParser):
          try:
            _ = arg.option_list
            def nodctrepr(v): return repr(v) if not isinstance(v,dict) else repr(v.keys())
            arg = [nodctrepr(elm) for elm in _]
          except:
            with open('hc902_err.log','a') as f:
              f.write("\n".join(arg))
            raise SystemExit
        if is_class(arg) or is_instance(arg):
          try:
            arg = auto_repr(arg)
            pre_pkld = Pkl(pickle.dumps(arg), type(arg), h_idx)
            return pre_pkld
          except:
            with open('hc879.log','a') as f:
              f.write(stackprinter.format(sys.exc_info()))
            raise SystemExit
        elif isinstance(arg,list):
          _ = [self.write_to_pickle(elm) for elm in arg]
          pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
          return pre_pkld
        elif has_dct(arg):
          _ = has_dct(arg)
          pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
          return pre_pkld
        else:
          with open('hc906_err.log','a') as f:
            f.write(stackprinter.format())
            f.write(repr(arg))
          raise SystemExit
      except AttributeError as err:
        if isinstance(arg,tuple):
          try:
            _ = [self.write_to_pickle(elm) for elm in arg]
            pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
            return pre_pkld
          except:
            with open('hc899','a') as f:
              f.write(stackprinter.format())
              f.write(repr(arg))
            raise SystemExit
        elif is_class(arg):
          arg = auto_repr(arg)
          pre_pkld = Pkl(pickle.dumps(arg), type(arg), h_idx)
          return pre_pkld
        elif is_instance(arg):
          arg = auto_repr(arg)
          pre_pkld = Pkl(pickle.dumps(arg), type(arg), h_idx)
          return pre_pkld
        elif isinstance(arg,dict):
          try:
            lst = []
            for k,v in arg.items():
              lst.append(f"{k}: {get_pickled_bytes(v)}")
            _ = "\n".join(lst)
            pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
            return pre_pkld
          except:
            print("AttributeError Unresolved 2")
        elif inspect.isfunction(arg):
          try:
            _ = is_function(arg)
            pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
            return pre_pkld
          except:
            print("AttributeError Unresolved 4")
            raise SystemExit
        elif isinstance(arg,list):
          _ = [self.write_to_pickle(elm) for elm in arg]
          pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
          return pre_pkld
        else:
          with open('hc952_err.log','a') as f:
            f.write(stackprinter.format())
            f.write(repr(arg))
          raise SystemExit
      except TypeError as err:
        if isinstance(arg,tuple):
          if is_class(arg[0]):
            _ = auto_repr(arg[0])
            pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
            return pre_pkld
          else:
            debug_error(arg,auto_repr(arg[0]),"TypeError")
            print("TypeError Unresolved 1")
            raise SystemExit
        elif isinstance(arg,dict):
          try:
            lst = []
            for k,v in arg.items():
              lst.append(f"{k}: {get_pickled_bytes(v)}")
            _ = "\n".join(lst)
            pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
            return pre_pkld
          except:
            print("TypeError Unresolved 2")
            raise SystemExit
        elif hasattr(arg,'__dict__'):
          try:
            d = arg.__dict__
            print(d)
            lst = []
            for k,v in d.items():
              lst.append(f"{k}: {repr(v)}")
            _ = "\n".join(lst)
            pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
            return pre_pkld
          except:
            print("TypeError Unresolved 3")
            raise SystemExit
        elif isinstance(arg,GeneratorType):
          try:
            _ = repr(list(arg))
            pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
            return pre_pkld
          except:
            print("TypeError Unresolved 4")
            raise SystemExit
        else:
          with open('hc999_err.log','a') as f:
            f.write(stackprinter.format())
            f.write(repr(arg))
          raise SystemExit
      except:
        with open('hc1004_err.log','a') as f:
          f.write(stackprinter.format())
          f.write(repr(arg))
        raise SystemExit

    def write_to_disk(pkld,og_arg=None,debug=False):
      pre_pkld, pkld_type, h_idx = pkld
      og_arg = f"{repr(og_arg)}\n"
      pkld_obj = f"{repr(pre_pkld)}\n"
      pkld_hex = f"{pickle.dumps(tuple( (h_idx,pkld_type,pre_pkld) )).hex()}\n"
      if debug:
        pkld_strori = Path(self.pickle_path).parent.joinpath('eventpickle_ori')
        with open(pkld_strori,'a') as f:
          f.write(og_arg)
        pkld_strarg = Path(self.pickle_path).parent.joinpath('eventpickle_arg')
        with open(pkld_strarg,'a') as f:
          f.write(pkld_obj)
      pkld_strhex = Path(self.pickle_path).parent.joinpath('eventpickle_hex')
      with open(pkld_strhex,'a') as f:
        f.write(pkld_hex)
      return pkld_strhex

    main(arg)

  def read_yaml(self):
    yaml = YAML(typ='unsafe')
    yaml_path = Path(self.yaml_path).parent.joinpath('eventyaml')
    with open(yaml_path) as f:
      yaml.load(f)

  def write_yaml(self,arg):
    try:
      if isinstance(arg,tuple) and isinstance(arg[1],BaseException):
        assert arg[2] is None or isinstance(arg[2],TracebackType), f"{info(arg)}"
        arg = traceback.format_exception_only(arg[0],arg[1])
      else:
        yaml = YAML(typ='unsafe')
        yaml.default_flow_style = False
        yaml_path = Path(self.yaml_path).parent.joinpath('eventyaml')
        with open(yaml_path,'a') as f:
          yaml.dump(arg,f)
    except:
      arg = repr(arg)
      with open('hc1060_errr.log','a') as f:
        f.write(stackprinter.format(sys.exc_info()))
        f.write(f"{arg=}")

  def read_json(self):
    jsn_path = Path(self.json_path).parent.joinpath('eventjson')
    with open(jsn_path,'a') as f:
      lines = f.read()
    jsn_lines = [jsonpickle.decode(line) for line in lines]
    return jsn_lines

  def write_json(self,arg):
    try:
      jsn = jsonpickle.encode(arg)
      jsn_path = Path(self.json_path).parent.joinpath('eventjson')
      with open(jsn_path,'a') as f:
        f.write(jsn+'\n')
    except:
      arg = repr(arg)
      with open('hc1077_err.log','a') as f:
        f.write(stackprinter.format(sys.exc_info()))
        f.write(f"{arg=}")

  def read_from_supplemental(self):
    pkld_strhex = Path(self.pickle_path).parent.joinpath('eventpickle_supp_hex')
    with open(pkld_strhex, 'r') as file:
      try:
        lines = file.readlines()
        decoded_lines = [bytes.fromhex(elm).strip() for elm in lines]
        unpkld_lines = [pickle.loads(elm) for elm in decoded_lines]
        return unpkld_lines
      except EOFError:
        raise

  def write_supplemental_pickle(
    self,
    filename_prefix,
    evt_knd,
    stack,
    evt_fnc,
    evt_src,
    h_idx):
    symbdct = {"call":"=>","line":"","exception":"!!","return":"<="}

    def main():
      try:
        supp_obj = make_supplemental()
        pkld = get_pickled(supp_obj)
        retval = write_pickled(pkld)
        return retval
      except:
        with open('hc1027.log','a') as f:
          f.write(stackprinter.format(sys.exc_info()))

    def make_supplemental():
      supp = Supplement(
        filename_prefix = SupplementalField(
          filename_prefix.mono,
          filename_prefix.poly),
        event_kind = SupplementalField(
          f"{evt_knd:9} ",
          f"{self.clrs(evt_knd,'KIND'):9} "),
        indent_len = SupplementalField(
          f"{len('   ' * (len(stack) - 1))}",
          f"{len('   ' * (len(stack) - 1))}"
        ),
        event_symbol = SupplementalField(
          symbdct[evt_knd],
          f"{self.clrs(symbdct[evt_knd],evt_knd.upper())} "),
        event_function = SupplementalField(
          evt_fnc,evt_fnc),
        event_source = SupplementalField(
          evt_src.strip(),evt_src.strip()),
        h_idx = SupplementalField(
          h_idx,h_idx
        )
      )
      return supp

    def get_pickled(supp_obj):
      pre_pkld = pickle.dumps(supp_obj)
      return pre_pkld

    def write_pickled(pkld):
      pkld_pth = Path(self.pickle_path).parent.joinpath('eventpickle_supp_obj')
      phex_pth = Path(self.pickle_path).parent.joinpath('eventpickle_supp_hex')
      pobj,phex = repr(pkld),pkld.hex()
      with open(pkld_pth,'a') as f:
        f.write(pobj+'\n')
      with open(phex_pth,'a') as f:
        f.write(phex+'\n')
      return True

    main()

  def __call__(self, event):
    count = next(self.count)
    # fmtd_arg = self.process_event_arg(event.arg)
    # self.write_to_pickle(event.arg,h_idx=count)
    self.write_json(event.arg)

    ident = event.module, event.function

    thread = threading.current_thread()
    stack = self.locals[thread.ident]

    pid_prefix = self.pid_prefix()
    thread_prefix = self.thread_prefix(event)
    filename_prefix = self.filename_prefix(event,count)
    if event.kind == 'call':
      # :event.arg: None = None
      code = event.code
      stack.append(ident)
      # output = self.output_format(
        # '{}{KIND}{:9} {}{COLOR}=>{NORMAL} {}({}{COLOR}{NORMAL}){RESET}\n',
        # pid_prefix,
        # thread_prefix,
        # filename_prefix_poly,
        # event.kind,
        # '   ' * (len(stack) - 1),
        # event.function,
        # ', '.join('{VARS}{VARS-NAME}{0}{VARS}={RESET}{1}'.format(
        #   var,
        #   event.locals.get(var, MISSING) if event.detached else self.try_repr(event.locals.get(var, MISSING)),
        #   **self.other_colors
        # ) for var in code.co_varnames[:code.co_argcount]),
        # COLOR=self.event_colors.get(event.kind),
        # )
      # self.write_output(output)
      self.write_supplemental_pickle(
        filename_prefix,
        event.kind,
        stack,
        event.function,
        event.source,
        count
      )
    elif event.kind == 'exception':
      # :event.arg: tuple = (exception, value, traceback)
      # output = self.output_format(
        # '{}{KIND}{:9} {}{COLOR} !{NORMAL} {}: {RESET}{}\n',
        # # pid_prefix,
        # # thread_prefix,
        # filename_prefix_poly,
        # event.kind,
        # '   ' * (len(stack) - 1),
        # event.function,
        # event.arg if event.detached else self.try_repr(event.arg),
        # COLOR=self.event_colors.get(event.kind),
        # )
      # self.write_output(output)
      self.write_supplemental_pickle(
        filename_prefix,
        event.kind,
        stack,
        event.function,
        event.source,
        count
      )
    elif event.kind == 'return':
      # :event.arg: = return value or `None` if exception
      # output = self.output_format(
        # '{}{KIND}{:9} {}{COLOR}<={NORMAL} {}: {RESET}{}\n',
        # # pid_prefix,
        # # thread_prefix,
        # filename_prefix_poly,
        # event.kind,
        # '   ' * (len(stack) - 1),
        # event.function,
        # event.arg if event.detached else self.try_repr(event.arg),
        # COLOR=self.event_colors.get(event.kind),
        # )
      # self.write_output(output)
      self.write_supplemental_pickle(
        filename_prefix,
        event.kind,
        stack,
        event.function,
        event.source,
        count
      )
      if stack and stack[-1] == ident:
        stack.pop()
    else:
      # :event.arg: = `None`
      # output = self.output_format(
        # '{}{KIND}{:9} {RESET}{}{}{RESET}\n',
        # # pid_prefix,
        # # thread_prefix,
        # filename_prefix_poly,
        # event.kind,
        # '   ' * len(stack),
        # self.try_source(event).strip(),
        # )
      # self.write_output(output)
      self.write_supplemental_pickle(
        filename_prefix,
        event.kind,
        stack,
        event.function,
        event.source,
        count
      )

def safe_repr(obj, maxdepth=5):
  if not maxdepth:
    return '...'
  obj_type = type(obj)
  newdepth = maxdepth - 1

  # specifically handle few of the container builtins that would normally do repr on contained values
  if isinstance(obj, dict):
    if obj_type is not dict:
      return '%s({%s})' % (
        obj_type.__name__,
        ',\n1@'.join('%s: %s' % (
          safe_repr(k, maxdepth),
          safe_repr(v, newdepth)
        ) for k, v in obj.items()))
    else:
      return '{%s}' % ',\n2@'.join('%s: %s' % (
        safe_repr(k, maxdepth),
        safe_repr(v, newdepth)
      ) for k, v in obj.items())
  elif isinstance(obj, list):
    if obj_type is not list:
      return '%s([%s])' % (obj_type.__name__, ',\n3@'.join(safe_repr(i, newdepth) for i in obj))
    else:
      return '[%s]' % ',\n4@'.join(safe_repr(i, newdepth) for i in obj)
  elif isinstance(obj, tuple):
    if obj_type is not tuple:
      return '%s(%s%s)' % (
        obj_type.__name__,
        ',\n'.join(safe_repr(i, newdepth) for i in obj),
        ',' if len(obj) == 1 else '')
    else:
      return '(%s%s)' % (',\n'.join(safe_repr(i, newdepth) for i in obj), ',' if len(obj) == 1 else '')
  elif isinstance(obj, set):
    if obj_type is not set:
      return '%s({%s})' % (obj_type.__name__, ',\n'.join(safe_repr(i, newdepth) for i in obj))
    else:
      return '{%s}' % ',\n'.join(safe_repr(i, newdepth) for i in obj)
  elif isinstance(obj, frozenset):
    return '%s({%s})' % (obj_type.__name__, ',\n'.join(safe_repr(i, newdepth) for i in obj))
  elif isinstance(obj, deque):
    return '%s([%s])' % (obj_type.__name__, ',\n'.join(safe_repr(i, newdepth) for i in obj))
  elif isinstance(obj, BaseException):
    return '%s(%s)' % (obj_type.__name__, ',\n'.join(safe_repr(i, newdepth) for i in obj.args))
  elif obj_type in (type, types.ModuleType,
                      types.FunctionType, types.MethodType,
                      types.BuiltinFunctionType, types.BuiltinMethodType,
                      io.IOBase):
    # hardcoded list of safe things. note that isinstance ain't used
    # (we don't trust subclasses to do the right thing in __repr__)
    return repr(obj)
  elif not has_dict(obj_type, obj):
    return repr(obj)
  else:
    # if the object has a __dict__ then it's probably an instance of a pure python class, assume bad things
    #  with side-effects will be going on in __repr__ - use the default instead (object.__repr__)
    return object.__repr__(obj)

def has_dict(obj_type, obj, tolerance=25):
  """
  A contrived mess to check that object doesn't have a __dit__ but avoid checking it if any ancestor is evil enough to
  explicitly define __dict__ (like apipkg.ApiModule has __dict__ as a property).
  """
  ancestor_types = deque()
  while obj_type is not type and tolerance:
    ancestor_types.appendleft(obj_type)
    obj_type = type(obj_type)
    tolerance -= 1
  for ancestor in ancestor_types:
    __dict__ = getattr(ancestor, '__dict__', None)
    if __dict__ is not None:
      if '__dict__' in __dict__:
        return True
  return hasattr(obj, '__dict__')

# CustomPrinter.safe_repr = safe_repr

class QueryConfig:
  """note: changes in __call__ methods are visible in ytdev not ytdf"""
  Config = namedtuple('Config' , 'query actions outputs filenames write_func base_path')

  def __init__(self):
    self.basedir = Path('/Users/alberthan/VSCodeProjects/vytd/src/youtube-dl')
    self.configs = []

  def write_func(self,outputs,filenames):
    for filename in filenames:
      fndir = filename.parent
      fndir.mkdir(parents=True,exist_ok=True)
    for output,filename in zip(outputs,filenames):
      with open(filename, 'a') as f:
        # f.write(f"{type(output)=}")
        # f.write(output.write())
        # f.write(f"{dir(output)=}")
        f.write(output)
    for filename in filenames:
      dirname = filename.parent
      new_pth_cmpts = dirname.relative_to(self.basedir)
      outdir = self.basedir.joinpath(new_pth_cmpts)
      fs = FileSplit(file=filename, splitsize=1_100_000, output_dir=outdir)
      fs.split()

  def eventpickle(self):
    base_path = self.basedir.joinpath('eventpickle').absolute()
    base_path.mkdir(parents=True,exist_ok=True)
    actions = [
      CustomPrinter(
        # stream=io.StringIO(),
        # stream=sys.stdout,
        repr_limit=4096,
        # repr_func=safe_repr,
        filename_alignment=10,
        # force_colors=False,
        base_path=base_path,
      ),
      # CallPrinter(),
    ]
    outputs = [action.stream for action in actions]
    filenames = [base_path.joinpath(filename).absolute() for filename in ['call.eventpickle.log']]
    write_func = partial(self.write_func,outputs,filenames)
    query = And(
      Q(filename_endswith=[".py"],
            filename_contains="youtube_dl",
            # kind='return',
            stdlib=True,
            actions=actions),
      ~Q(filename_endswith=["hunterconfig.py","evt_loader.py"]))
    c = QueryConfig.Config(query,actions,outputs,filenames,write_func,base_path)
    self.configs.append(c)
    return c
