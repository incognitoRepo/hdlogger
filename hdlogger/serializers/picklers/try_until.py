import stackprinter, sys, copyreg
import dill as pickle

from pickle import SETITEM
from io import StringIO, BytesIO
from prettyprinter import pformat
from hdlogger.utils import *
from typing import Union, Any, Dict, List

from dill._dill import stack, _main_module
from dill.settings import settings
from numpy import ufunc as NumpyUfuncType
from numpy import ndarray as NumpyArrayType

import hdlogger

ClassType = TypeType = type

class ErrorFlag:
  def __init__(self,arg):
    self.arg = arg

  def __str__(self):
    s = f"TryUntilPickleable._with_func failed to make {arg} pickleable"
    return s

class TryUntil:
  def __init__(self,funcs,arg):
    self.funcs = funcs
    self.arg = self.initialize_arg(arg)

  def initialize_arg(self,arg):
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
    if isinstance(arg,(List,Dict)):
      return self._try_until_container(funcs,arg)
    else:
      return self._try_until(funcs,arg)

  def _try_until(self,funcs=[],arg=None):
    """iterates thru a list of functions, returning on the first success"""
    l,rv_or_false = [], None
    for func in funcs:
      rv_or_false = self._with_func(func,arg)
      if not isinstance(rv_or_false,ErrorFlag):
        return rv_or_false
    else:
      wf((
        f"\t{pformat(funcs)=}\n"
        f"\t{pformat(arg)=}\n"
      ),'logs/_try_until.error.log','a')
      raise SystemExit('_try_until: all funcs failed to create a pickleable obj.')
      l.append(rv_or_false)
    return l

  def _try_until_container(self,funcs=[],args=None):
    """for container types: e.g., List, Dict"""
    l = []
    for arg in args:
      # wf('arg: '+pformat(arg)+'\n','logs/try_until.log','a')
      l.append(self._try_until(funcs,arg))
      # wf('l: '+pformat(l)+'\n','logs/try_until.log','a')
    return l

  def _with_func(self,func,arg) -> Union[type(False),Any]:
    try:
      rv = func(arg)
    except:
      fid = id(func)
      wf(stackprinter.format(sys.exc_info())+'\n',f'logs/tryuntil{fid}.log', 'a')
      return ErrorFlag(msg=f"TryUntil._with_func failed to make {arg} pickleable")
    else:
      return func(arg)

class TryUntilPickleable(TryUntil):
  def __init__(self,funcs,arg):
    super().__init__(funcs=funcs,arg=arg)
    hdlogger.serializers.initialize_copyreg()

  def _with_func(self,func,arg):
    try:
      rv = pickle.loads(pickle.dumps(func(arg)))
    except:
      fid = id(func)
      wf(stackprinter.format(sys.exc_info()),f'logs/tryuntilpkl{fid}.log', 'w')
      return ErrorFlag(arg)
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

filtered_modules = {
  'ctypes': lambda k,v: {k:repr(v)}
}
def module_filters(obj):
  if hasattr(obj,'__module__') and (obj.__module__ in filtered_modules):
    return filtered_modules[obj.__module__](obj)

class FilteredPickler(pickle.Pickler):
  def __init__(self, *args, **kwds):
      self.filtered_modules = kwds.get('filtered_modules',filtered_modules)
      super().__init__(*args, **kwds)

  def save(self, obj, save_persistent_id=True):
    # filter modules
    obj = module_filters(obj)
    try:
      return super().save(obj, save_persistent_id=True)
    except:
      return repr(obj)

if sys.hexversion < 0x03040000:
  GENERATOR_FAIL = True
else: GENERATOR_FAIL = False

def ndarraysubclassinstance(obj):
  if type(obj) in (TypeType, ClassType):
    return False # all classes return False
  try: # check if is ndarray, and elif is subclass of ndarray
    cls = getattr(obj, '__class__', None)
    if cls is None: return False
    elif cls is TypeType: return False
    elif 'numpy.ndarray' not in str(getattr(cls, 'mro', int.mro)()):
      return False
  except ReferenceError: return False # handle 'R3' weakref in 3.x
  except TypeError: return False
  # anything below here is a numpy array (or subclass) instance
  __hook__() # import numpy (so the following works!!!)
  # verify that __reduce__ has not been overridden
  NumpyInstance = NumpyArrayType((0,),'int8')
  if id(obj.__reduce_ex__) == id(NumpyInstance.__reduce_ex__) and \
    id(obj.__reduce__) == id(NumpyInstance.__reduce__): return True
  return False

def numpyufunc(obj):
  if type(obj) in (TypeType, ClassType):
    return False # all classes return False
  try: # check if is ufunc
    cls = getattr(obj, '__class__', None)
    if cls is None: return False
    elif cls is TypeType: return False
    if 'numpy.ufunc' not in str(getattr(cls, 'mro', int.mro)()):
      return False
  except ReferenceError: return False # handle 'R3' weakref in 3.x
  except TypeError: return False
  # anything below here is a numpy ufunc
  return True
