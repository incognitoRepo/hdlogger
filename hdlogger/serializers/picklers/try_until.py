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

# from ..pickle_dispatch import pickleable_dispatch, initialize_copyreg
import hdlogger
from pprint import pformat
dir_hdlogger = pformat(dir(hdlogger))
# mod = __module__
wf(f"{dir_hdlogger}\n",'logs/try_until.module.log','a')


ClassType = TypeType = type

ErrorFlag = type("ErrorFlag",(object,),{"msg":None})
ErrorFlag2 = type("ErrorFlag2",(),{})

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
    # wf(f"{funcs=}\n",'logs/try_until.log','a')
    # wf(f"{arg=}\n",'logs/try_until.log','a')
    if isinstance(arg,(List,Dict)):
      return self._try_until_container(funcs,arg)
    else:
      return self._try_until(funcs,arg)

  def _try_until(self,funcs=[],arg=None):
    """iterates thru a list of functions, returning on the first success"""
    # wf(f"in _try_until:\n",'logs/try_until.log','a')
    # wf('\targ: '+pformat(arg)+'\n','logs/try_until.log','a')
    l,rv_or_false = [], None
    for func in funcs:
      # wf('\tfunc: '+pformat(func)+'\n','logs/try_until.log','a')
      rv_or_false = self._with_func(func,arg)
      # wf('\trv_or_false: '+pformat(rv_or_false)+'\n','logs/try_until.log','a')
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
    # wf(f"in _try_until_container:\n",'logs/try_until.log','a')
    funcs = funcs if funcs else self.funcs
    args = args if args else self.arg
    # wf('args: '+pformat(args)+'\n','logs/try_until.log','a')
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

  def _with_func(self,func,arg):
    try:
      rv = pickle.loads(pickle.dumps(func(arg)))
    except:
      fid = id(func)
      wf(stackprinter.format(sys.exc_info()),f'logs/tryuntilpkl{fid}.log', 'w')
      return ErrorFlag(msg=f"TryUntilPickleable._with_func failed to make {arg} pickleable")
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
  'ctypes': lambda obj: repr(obj)
}
def module_filters(obj):
  if hasattr(obj,'__module__') and (obj.__module__ in filtered_modules):
    return filtered_modules[obj.__module__]

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

def filtered_dump(obj, file, protocol=None, byref=None, fmode=None, recurse=None):#, strictio=None):
    """pickle an object to a file"""
    strictio = False #FIXME: strict=True needs cleanup
    if protocol is None: protocol = settings['protocol']
    if byref is None: byref = settings['byref']
    if fmode is None: fmode = settings['fmode']
    if recurse is None: recurse = settings['recurse']
    stack.clear()  # clear record of 'recursion-sensitive' pickled objects
    pik = FilteredPickler(file, protocol)
    initialize_copyreg()
    pik.dispatch_table = copyreg.dispatch_table.copy()
    pik._main = _main_module
    # apply kwd settings
    pik._byref = bool(byref)
    pik._strictio = bool(strictio)
    pik._fmode = fmode
    pik._recurse = bool(recurse)
    # register if the object is a numpy ufunc
    # thanks to Paul Kienzle for pointing out ufuncs didn't pickle
    if NumpyUfuncType and numpyufunc(obj):
        @register(type(obj))
        def save_numpy_ufunc(pickler, obj):
            log.info("Nu: %s" % obj)
            FilteredPickler.save_global(pickler, obj)
            log.info("# Nu")
            return
        # NOTE: the above 'save' performs like:
        #   import copy_reg
        #   def udump(f): return f.__name__
        #   def uload(name): return getattr(numpy, name)
        #   copy_reg.pickle(NumpyUfuncType, udump, uload)
    # register if the object is a subclassed numpy array instance
    if NumpyArrayType and ndarraysubclassinstance(obj):
        @register(type(obj))
        def save_numpy_array(pickler, obj):
            log.info("Nu: (%s, %s)" % (obj.shape,obj.dtype))
            npdict = getattr(obj, '__dict__', None)
            f, args, state = obj.__reduce__()
            pickler.save_reduce(_create_array, (f,args,state,npdict), obj=obj)
            log.info("# Nu")
            return
    # end hack
    if GENERATOR_FAIL and type(obj) == GeneratorType:
        msg = "Can't pickle %s: attribute lookup builtins.generator failed" % GeneratorType
        raise PicklingError(msg)
    else:
        pik.dump(obj)
    stack.clear()  # clear record of 'recursion-sensitive' pickled objects
    return

def filtered_dumps(obj, protocol=None, byref=None, fmode=None, recurse=None):#, strictio=None):
    """pickle an object to a string"""
    file = BytesIO()
    filtered_dump(obj, file, protocol, byref, fmode, recurse)#, strictio)
    return file.getvalue()

def filtered_load(file, ignore=None):
    """unpickle an object from a file"""
    if ignore is None: ignore = settings['ignore']
    pik = pickle.Unpickler(file)
    initialize_copyreg()
    pik._main = _main_module
    # apply kwd settings
    pik._ignore = bool(ignore)
    obj = pik.load()
    if type(obj).__module__ == getattr(_main_module, '__name__', '__main__'):
        if not ignore:
            # point obj class to main
            try: obj.__class__ = getattr(pik._main, type(obj).__name__)
            except (AttributeError,TypeError): pass # defined in a file
   #_main_module.__dict__.update(obj.__dict__) #XXX: should update globals ?
    return obj

def filtered_loads(str, ignore=None):
    """unpickle an object from a string"""
    file = BytesIO(str)
    return filtered_load(file, ignore)
