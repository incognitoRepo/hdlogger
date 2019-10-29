# vscode-fold=1
import dis, inspect
import logging
import jsonpickle as jsonpkl
from pathlib import Path
from collections import namedtuple, Counter
from itertools import count
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

UNSET = object()
class Event:
  DATA = SimpleNamespace(dataset = set())
  COUNT = count()
  def __init__(
    self,
    frame:FrameType,event:str,arg:Any,
    write_flag:bool=True,
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
    jp = jsonpkl.encode(pfss._asdict())
    jsonpath = Path('_jsnpkl.json').resolve()
    with open(jsonpath,'a') as f:
      f.write(jp+'\n')
    return jsonpath

PackedFrameStrings = namedtuple(
  'PackedFrameStrings',
  'sb cs eas fs fcs fc_dcis fc_dass fc_dgis fc_flss eb'
)
def get_strs(event,counter=""):
  frame = event.frame
  arg = event.arg
  fc = frame.f_code
  bnr = f"\n{'=='*40}" # start banner
  cnt = event.count # counter str
  evt = event
  arg = arg
  mod = event.module
  frm = frame
  cod = frame.f_code
  dis_info = dis.code_info(fc)
  dis_ass = dis.disassemble(fc)
  dis_instr = dis.get_instructions(fc)
  # fc_dgis:str  = '\n'.join([repr(elm) for elm in fc_dgil])
  dis_lsrts = dis.findlinestarts(fc)
  # fc_flss:str  = '\n'.join([repr(elm) for elm in fc_flsl])
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
