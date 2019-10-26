from types import (
  FrameType
)
from .constants import (
  SITE_PACKAGES_PATHS,
  SYS_PREFIX_PATHS,
  CYTHON_SUFFIX_RE
)

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
  def __init__(self,frame:FrameType,event:str,arg):
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

  @property
  def module(self):
    if self._module is UNSET:
      module = self.frame.f_globals.get('__name__','')
      if module is None:
        module = ''
      self._module = module
    return self._module

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
