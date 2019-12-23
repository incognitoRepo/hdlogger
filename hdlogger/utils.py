import contextlib, stackprinter

from itertools import count
from pathlib import Path
from typing import Iterable, Container, Collection

def wf(obj,filename,mode="a"):
  end = f"\n{'-~'*40}\n"
  path = Path(filename)
  if not path.parent.exists():
    path.mkdir(parents=True, exist_ok=True)
  if isinstance(obj, bytes):
    nobj = str(obj)
    s = f"bytes instance:\n{obj=}\n{nobj=}{end}"
  elif isinstance(obj, Container) and not isinstance(obj,str):
    nobj = "\n".join(str(obj)) + "\n"
    s = f"container instance:\n{obj=}\n{nobj=}{end}"
  else:
    nobj = obj
  s = f"write obj:\n{str(nobj)=}\n{nobj=}{end}"
  with path.open(mode,encoding="utf-8") as f: f.write(str(nobj))
  assert path.exists()
  # with open('logs/history.log','a') as f: f.write(str(path)+'\n')

def rf(filename, mode="r"):
  path = Path(filename)
  with path.open(mode) as f:
    lines = f.readlines()
  return lines

def ws(spaces=0,tabs=0): # whitespace
  indent_size = spaces + (tabs * 2)
  whitespace_character = " "
  return f"{whitespace_character * indent_size}"

def _c(s,modifier=0,intensity=3,color=0):
  """
  mod      ::= 0(reset)|1(bold)|2(faint)|3(italic)|4(underline)
  int      ::= 9(intense fg) | 3(normal bg)
  clr      ::= 0(blk)|1(red)|2(grn)|3(ylw)|4(blu)|5(mag)|6(cyn)|7(wht)
  """
  escape = "\x1b["
  reset_modifier = 0
  ns = f"{escape}{modifier};{intensity}{color}m{s}{escape}{reset_modifier}m"
  return ns

def c(s,arg=None):
  if WRITE is True: return s
  """apply color to a string"""
  if s == 'call': return _c(s,modifier=1,intensity=9,color=2)
  if s == 'line': return _c(s,modifier=2,intensity=3,color=0)
  if s == 'return': return _c(s,modifier=1,intensity=9,color=3)
  if s == 'exception': return _c(s,modifier=1,intensity=9,color=1)

  if arg:
    if arg == 'vars': return _c(s,modifier=0,intensity=9,color=5)
    # symbols
    if arg == 'call': return _c(s,modifier=1,intensity=9,color=2)
    if arg == 'line': return _c(s,modifier=2,intensity=3,color=0)
    if arg == 'return': return _c(s,modifier=1,intensity=9,color=3)
    if arg == 'exception': return _c(s,modifier=1,intensity=9,color=1)

def checkfuncs(funcs,arg):
  def checkfunc(func,arg):
    with contextlib.suppress(Exception):
      return func(arg)
  for func in funcs:
    if funcres:= checkfunc(func,arg) is not None:
      return funcres
    else:
      return None
  raise Exception("DEhd.checkfuncs: all funcs failed")

def print_attrs(obj):
  attrnames = [attr for attr in dir(obj) if not attr.startswith('_')]
  _ = operator.attrgetter(*attrnames)
  attrvals = [getattr(obj,name) for name in attrnames]
  d = {k:v for k,v in zip(attrnames,attrvals)}
  cpprint(d)
  return d

