# vscode-fold=1
import dis, inspect
import jsonpickle as jsonpkl
from pathlib import Path
from collections import namedtuple, Counter
from itertools import count, tee
from types import SimpleNamespace, GeneratorType
import stackprinter
from linecache import getline

from typing import Dict,List,Union,Any
from types import (
  FrameType
)
from .constants import (
  SITE_PACKAGES_PATHS,
  SYS_PREFIX_PATHS,
  CYTHON_SUFFIX_RE,
  STARTSWITH_PASS_MODULES,
)

def filter(event_module):
  em = event_module
  for MOD in STARTSWITH_PASS_MODULES:
    if em.startswith(MOD):
      return True
  return False

def filter_only(event_module,target_modules:list):
  em = event_module
  for tmod in target_modules:
    if tmod in em:
      return True
  return False

def get_answer():
  """Get an answer."""
  return True

UNSET = object()
class Event:
  DATA = SimpleNamespace(kind="",dataset=set())
  COUNT = count()
  def __init__(
    self,
    frame:FrameType,event:str,arg:Any,
    write_flag:bool=False,
    collect_data:bool=False,
  ):
    self.frame = frame
    self.count = next(self.COUNT)
    self.module = self.frame.f_globals.get('__name__','')
    self.filename = self.frame.f_code.co_filename
    self.lineno = self.frame.f_lineno
    src = getline(self.filename, self.lineno, self.frame.f_globals)
    self.source = src
    this_func = "\x1b[2;3;96mEvent\x1b[0m"

    self.event = event
    self.test_frame(arg)
    self.arg = arg
    self.arg_type = type(arg)
    # self._code = UNSET
    # self._fullsource = UNSET
    # self._function_object = UNSET
    # self._function = UNSET
    # self._globals = UNSET
    # self._lineno = UNSET
    # self._locals = UNSET

    self._stdlib = UNSET
    # self._threadidn = UNSET
    # self._threadname = UNSET
    # self._thread = UNSET
    if collect_data: self.setup_data_collection(collect_data)
    if write_flag: self.write_trace()
    if arg:
      print(f"    in {this_func}: {self.count=}, {self.module=}, {event=}, {arg=}", end="")
      print(f", isinstance \x1b[1;34m{isinstance(arg,GeneratorType)}\x1b[0m")
    else:
      print(f"    in {this_func}: {self.count=}, {self.module=}, {event=}, {arg=}",end="")
      print(f", isinstance \x1b[1;34m{isinstance(arg,GeneratorType)}\x1b[0m")

  def test_frame(self,arg):
    if 'rv' in self.frame.f_locals:
      pass

  def test_frame1(self,arg):
    if not arg: arg = "null"
    if 'rv' in self.frame.f_locals:
      cf = inspect.currentframe()
      print(self.frame.f_locals.keys())
      print(cf.f_locals['self'].frame.f_locals.keys())
      print(list(self.frame.f_locals['rv']))
      self.frame.f_locals['rv2'] = [333]
      import ipdb; ipdb.set_trace()
      print(self.frame.f_locals.keys())
      print(list(self.frame.f_locals['rv2']))
      fl = list(self.frame.f_locals['rv2'])
      fl1,fl2,fl3 = (elm for elm in fl),(elm for elm in fl),(elm for elm in range(3))
      self.frame.f_locals['rv'] = fl3
      print(f"  {isinstance(arg,GeneratorType)=}, {list(arg)}")
      print(f"  {isinstance(fl2, GeneratorType)=}, {list(fl2)=}")
      print(f"  {list(arg)}")
      print(f"  {list(fl1)=}")
      self.frame.f_locals['rv'] = [elm for elm in range(3)]
      print(f"  {isinstance(self.frame.f_locals['rv'],GeneratorType)=}, {list(self.frame.f_locals['rv'])=}")

  def test_frame2(self,arg):
    if not arg: arg = "null"
    print(self.frame.f_globals.keys())
    if 'rv' in self.frame.f_globals:
      cf = inspect.currentframe()
      print(self.frame.f_globals.keys())
      print(cf.f_globals['self'].frame.f_globals.keys())
      print(list(self.frame.f_globals['rv']))
      self.frame.f_globals['rv2'] = [333]
      import ipdb; ipdb.set_trace()
      print(self.frame.f_globals.keys())
      print(list(self.frame.f_globals['rv2']))
      fl = list(self.frame.f_globals['rv2'])
      fl1,fl2,fl3 = (elm for elm in fl),(elm for elm in fl),(elm for elm in range(3))
      self.frame.f_globals['rv'] = fl3
      print(f"  {isinstance(arg,GeneratorType)=}, {list(arg)}")
      print(f"  {isinstance(fl2, GeneratorType)=}, {list(fl2)=}")
      print(f"  {list(arg)}")
      print(f"  {list(fl1)=}")
      self.frame.f_globals['rv'] = [elm for elm in range(3)]
      print(f"  {isinstance(self.frame.f_globals['rv'],GeneratorType)=}, {list(self.frame.f_globals['rv'])=}")

  @property
  def stdlib(self):
    if self._stdlib is UNSET:
      module_parts = self.module.split('.')
      if 'pkg_resources' in module_parts:
        self._stdlib = True
      elif self.filename == '<frozen importlib._bootstrap>':
        self._stdlib = True
      elif self.filename.startswith(SITE_PACKAGES_PATHS):
        # if it's in site-packages then its definitely not stdlib
        self._stdlib = False
      elif self.filename.startswith(SYS_PREFIX_PATHS):
        self._stdlib = True
      else:
        self._stdlib = False
    return self._stdlib

  @property
  def data(self):
    return self.DATA

  def setup_data_collection(self,which_data):
    self.DATA.kind = which_data
    self.DATA.dataset.add(getattr(self,which_data))

  def write_data(self):
    filepath = Path(f"_{self.DATA.kind}_data.log").resolve()
    with open(filepath,"w") as f:
      f.write('\n'.join([elm for elm in self.DATA.dataset if elm is not None]))
    assert filepath.exists(), f'failed to write data to {filepath}'
    return filepath

  def write_trace(self):
    pfss = get_strs(self,self.COUNT)
    jp = jsonpkl.encode(pfss)
    jsonpath = Path('_jsnpkl.json').resolve()
    # if pfss['arg']:
      # print(f'      cnt({pfss["cnt"]}): {pfss["arg"]=}')
    with open(jsonpath,'a') as f:
      f.write(jp+'\n')
    return jsonpath

def get_strs(event,counter=""):
  packed_frame_strings = {
    "cnt": event.count,
    "evt": event,
    "arg": event.arg,
    "mod": event.module,
    "frm": event.frame,
    "cod": event.frame.f_code,
    "atyp": event.arg_type,
    "dis_bc": dis.Bytecode(event.frame.f_code)
  }
  return packed_frame_strings

TracerKillPack = namedtuple(
  'TracerKillPack',
  'frame event arg'
)
def get_tracer_kill_pack():
  tkp = TracerKillPack(
    inspect.currentframe(),
    'kill',
    None)
  return tkp
