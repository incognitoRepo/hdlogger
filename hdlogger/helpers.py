# vscode-fold=1
import dis, inspect
import jsonpickle as jsonpkl
from pathlib import Path
from collections import namedtuple, Counter
from itertools import count, tee
from types import SimpleNamespace, GeneratorType

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
  DATA = SimpleNamespace(dataset = set())
  COUNT = count()
  def __init__(
    self,
    frame:FrameType,event:str,arg:Any,
    write_flag:bool=False,
    collect_data:bool=False,
  ):
    self.count = next(self.COUNT)
    self.frame = frame
    self.event = event
    self.arg = arg
    # self._code = UNSET
    self._filename = UNSET
    # self._fullsource = UNSET
    # self._function_object = UNSET
    # self._function = UNSET
    # self._globals = UNSET
    # self._lineno = UNSET
    # self._locals = UNSET
    self._module = UNSET
    # self._source = UNSET
    self._stdlib = UNSET
    # self._threadidn = UNSET
    # self._threadname = UNSET
    # self._thread = UNSET
    if collect_data: self.setup_data_collection(collect_data)
    if write_flag: self.write_trace()

  @property
  def module(self):
    if self._module is UNSET:
      module = self.frame.f_globals.get('__name__','')
      if module is None:
        module = ''
      self._module = module
    return self._module

  @module.setter
  def module(self,module):
    self._module = module
    if self.DATA.kind == 'module':
      self.DATA.dataset.add(self._module)

  @property
  def filename(self):
    if self._filename is UNSET:
      filename = self.frame.f_code.co_filename
      if not filename:
        filename = self.frame.f_globals.get('__file__')
      if not filename:
        filename = ''
      elif filename.endswith(('.pyc', '.pyo')):
        filename = filename[:-1]
      elif filename.endswith(('.so', '.pyd')):
        basename = CYTHON_SUFFIX_RE.sub('', filename)
        for ext in ('.pyx', '.py'):
          cyfilename = basename + ext
          if exists(cyfilename):
            filename = cyfilename
            break

      self._filename = filename
    return self._filename

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
      f.write('\n'.join(self.DATA.dataset))
    assert filepath.exists(), f'failed to write data to {filepath}'
    return filepath

  def write_trace(self):
    pfss = get_strs(self,self.COUNT)
    jp = jsonpkl.encode(pfss)
    jsonpath = Path('_jsnpkl.json').resolve()
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
