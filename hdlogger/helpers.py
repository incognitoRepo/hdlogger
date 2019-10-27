# vscode-fold=1
import dis, inspect
import logging
from collections import namedtuple
from types import SimpleNamespace

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

class MockFrame:
  def string(self):
    example = "<frame at 0x108756e50, file '<ipython-input-1-24d5ecc75ccb>', line 1, code <module>>"
    print(f"{example=}")

  def attributes(self,verbose=False):
    attrsv = ['f_back','f_builtins',
      'f_code','f_globals','f_lasti',
      'f_lineno','f_locals','f_trace',
      'f_trace_lines','f_trace_opcodes']
    attrs = ['f_back','f_code','f_lasti',
      'f_lineno','f_trace','f_trace_lines',
      'f_trace_opcodes']
    attrsj = '\n'.join(attrs)
    print(attrsj)
    return attrs

  def get_attributes(self,f):
    if f:
      attrs = self.attributes(verbose=False)
      d = {k:getattr(f,k) for k in attrs}
      for k,v in d.items():
        print(f"{k}={v}")
    else:
      raise Exception

class MockCode:
  def string(self):
    example = '<code object <module> at 0x106c22240, file "<ipython-input-1-24d5ecc75ccb>", line 1>'
    print(f"{example=}")

  def attributes(self,verbose=False):
    attrsv = [
      'co_argcount',
      'co_cellvars',
      'co_code',
      'co_consts',
      'co_filename',
      'co_firstlineno',
      'co_flags',
      'co_freevars',
      'co_kwonlyargcount',
      'co_lnotab',
      'co_name',
      'co_names',
      'co_nlocals',
      'co_posonlyargcount',
      'co_stacksize',
      'co_varnames']
    attrs = [
      'co_argcount',
      'co_cellvars',
      'co_code',
      'co_consts',
      'co_filename',
      'co_firstlineno',
      'co_flags',
      'co_freevars',
      'co_kwonlyargcount',
      'co_lnotab',
      'co_name',
      'co_names',
      'co_nlocals',
      'co_posonlyargcount',
      'co_stacksize',
      'co_varnames']
    attrsj = '\n'.join(attrs)
    print(attrsj)
    return attrs

  def get_attributes(self,f):
    if f:
      attrs = self.attributes(verbose=False)
      d = {k:getattr(fc,k) for k in attrs}
      for k,v in d.items():
        print(f"{k}={v}")
    else:
      raise Exception


UNSET = object()
class Event:
  DATA = SimpleNamespace()
  DATA.dataset = set()

  def __init__(self,
      frame:FrameType,event:str,arg:Any,
      collect_data:bool=False):
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

  def setup_data_collection(self,which_data):
    self.DATA.kind = which_data
    self.DATA.dataset.add(getattr(self,which_data))

  @property
  def data(self):
    return self.DATA

PackedFrameStrings = namedtuple(
  'PackedFrameStrings',
  'sb cs eas fs fcs fc_dcis fc_dass fc_dgis fc_flss eb'
)
def get_strs(event,counter=""):
  frame = event.frame
  fc = frame.f_code
  sb = f"\n{'=='*40}" # start banner
  cs = f"{counter=}\n" # counter str
  eas = f"{event=}\n{arg=}\n" # event & arg str
  ems = f"{event.module=}\n"
  fs = f"{frame=}\n"
  fcs = f"{frame.f_code=}\n"
  fc_dcis = f"{dis.code_info(fc)=}"
  fc_dass = f"{dis.disassemble(fc)=}"
  fc_dgil:List = dis.get_instructions(fc)
  fc_dgis:str  = '\n'.join(fc_dgil)
  fc_flsl:List = dis.findlinestarts(fc)
  fc_flss:str  = '\n'.join(fc_flsl)
  eb = f"\n{'=='*40}" # end banner
  pfss = PackedFrameStrings(
    sb,cs,eas,fs,fcs,fc_dcis,fc_dass,fc_dgis,fc_flss,eb
  )
  return pfss

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
