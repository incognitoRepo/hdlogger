import stackprinter, sys
import dill as pickle

from prettyprinter import pformat
from hdlogger.utils import *
from typing import Union, Any, Dict, List


class TryUntil:
  def __init__(self,funcs,arg):
    self.funcs = funcs
    self.arg = TryUntil.initialize_arg(arg)

  @classmethod
  def initialize_arg(cls,arg):
    if isinstance(arg,type({}.values())):
      arg = list(arg)
    else:
      arg = arg
    return arg

  def try_until(self,funcs=[],arg=None):
    """returns: List[False,Any]
        Any: the return value of func(arg)
        func: makes arg `pickleable`
    """
    funcs = funcs if funcs else self.funcs
    arg = arg if arg else self.arg
    if isinstance(arg,(List,Dict)):
      return self._try_until_container(funcs,arg)
    else:
      return self._try_until(funcs,arg)

  def _try_until(self,funcs=[],arg=None):
    """iterates thru a list of functions, returning on the first success"""
    funcs = funcs if funcs else self.funcs
    arg = arg if arg else self.arg
    l,rv_or_false = [], None
    for func in funcs:
      rv_or_false = self._with_func(func,arg)
      if rv_or_false:
        return rv_or_false
    else:
      wf((
        f"{pformat(funcs)=}"
        f"{pformat(arg)=}"
      ),'logs/_try_until.error.log','a')
      raise SystemExit('_try_until: all funcs failed to create a pickleable obj.')
      l.append(rv_or_false)
    return l

  def _try_until_container(self,funcs=[],args=None):
    """for container types: e.g., List, Dict"""
    funcs = funcs if funcs else self.funcs
    args = args if args else self.arg
    l = []
    for arg in args:
      l.append(self._try_until(funcs,arg))
    return l

  def _with_func(self,func,arg) -> Union[type(False),Any]:
    try:
      rv = func(arg)
    except:
      fid = id(func)
      wf(stackprinter.format(sys.exc_info()),f'logs/tryuntil{fid}.log', 'a')
      return False
    else:
      return func(arg)


class TryUntilPickleable(TryUntil):
  def __init__(self,funcs,arg):
    super().__init__(funcs=funcs,arg=arg)

  def _with_func(self,func,arg):
    try:
      rv = pickle.loads(pickle.dumps(func(arg)))
    except:
      fid = id(func)
      wf(stackprinter.format(sys.exc_info()),f'logs/tryuntilpkl{fid}.log', 'w')
      return False
    else:
      return pickle.loads(pickle.dumps(func(arg)))

def try_until_pkl(funcs,arg):
  tup = TryUntilPickleable(funcs,arg)
  rvl = tup.try_until()
  return rvl

def pickle_roundtrip(funcs,obj):
  """drop-in replacement for pickle.loads(pickle.dumps(obj))"""
  funcs = [lambda obj: pickle.loads(pickle.dumps(obj))]
  tup = TryUntilPickleable(funcs,obj)
  rvl = tup.try_until()
  pickleable_value = next(x for x in rvl if x) # raises StopIteration if not any(rvl)
  return pickleable_value

if __name__ == "__main__":
  def f1(arg):
    1/0

  def f2(arg):
    1 + 'a'

  def f3(arg):
    print(arg)
    return f"432333{arg}"

  def f4(arg):
    return 'aq'

  fs = [f1,f2,f3,f4]

  arg = ['memes']
  tu = TryUntil(fs, arg)
  from ipdb import set_trace as st;st()
  print(tu)
