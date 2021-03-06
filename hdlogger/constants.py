# vscode-fold=1
import collections
import os
import site
import sys
import re
from distutils.sysconfig import get_python_lib

STARTSWITH_PASS_MODULES = [
  'IPython','traitlets',
  'logging', 'hdlogger',
  'inspect','_','tokenize',
  'contextlib','re','textwrap',
  'os','warnings','traceback',
  'functools','types',
  'genericlib','genericpath',
  'collections','typing',
  'threading','namedtuple'
  'pluggy','importlib',
  '_pytest','unittest',
  'ast',
  'py._io.terminalwriter', 'py._path',
  'shutil',
  'posixpath','pathlib',
  'sre_parse','sre_compile',
  'namedtuple_CaptureResult'
]

SITE_PACKAGES_PATHS = set()
if hasattr(site, 'getsitepackages'):
  SITE_PACKAGES_PATHS.update(site.getsitepackages())
if hasattr(site, 'getusersitepackages'):
  SITE_PACKAGES_PATHS.add(site.getusersitepackages())
SITE_PACKAGES_PATHS.add(get_python_lib())
SITE_PACKAGES_PATHS = tuple(SITE_PACKAGES_PATHS)

SYS_PREFIX_PATHS = set((
  sys.prefix,
  sys.exec_prefix,
  os.path.dirname(os.__file__),
  os.path.dirname(collections.__file__),
))
for prop in 'real_prefix', 'real_exec_prefix', 'base_prefix', 'base_exec_prefix':
  if hasattr(sys, prop):
    SYS_PREFIX_PATHS.add(getattr(sys, prop))
SYS_PREFIX_PATHS = tuple(SYS_PREFIX_PATHS)

CYTHON_SUFFIX_RE = re.compile(r'([.].+)?[.](so|pyd)$', re.IGNORECASE)
