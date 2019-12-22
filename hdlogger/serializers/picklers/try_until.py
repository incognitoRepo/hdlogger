import stackprinter, sys, copyreg
import dill as pickle

from io import StringIO
from prettyprinter import pformat
from hdlogger.utils import *
from typing import Union, Any, Dict, List

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
    wf(f"{funcs=}\n",'logs/try_until.log','a')
    wf(f"{arg=}\n",'logs/try_until.log','a')
    if isinstance(arg,(List,Dict)):
      return self._try_until_container(funcs,arg)
    else:
      return self._try_until(funcs,arg)

  def _try_until(self,funcs=[],arg=None):
    """iterates thru a list of functions, returning on the first success"""
    wf(f"in _try_until:\n",'logs/try_until.log','a')
    wf('\targ: '+pformat(arg)+'\n','logs/try_until.log','a')
    l,rv_or_false = [], None
    for func in funcs:
      wf('\tfunc: '+pformat(func)+'\n','logs/try_until.log','a')
      rv_or_false = self._with_func(func,arg)
      wf('\trv_or_false: '+pformat(rv_or_false)+'\n','logs/try_until.log','a')
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
    wf(f"in _try_until_container:\n",'logs/try_until.log','a')
    funcs = funcs if funcs else self.funcs
    args = args if args else self.arg
    wf('args: '+pformat(args)+'\n','logs/try_until.log','a')
    l = []
    for arg in args:
      wf('arg: '+pformat(arg)+'\n','logs/try_until.log','a')
      l.append(self._try_until(funcs,arg))
      wf('l: '+pformat(l)+'\n','logs/try_until.log','a')
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

class FilteredPickler(pickle.Pickler):
  def __init__(self, *args, **kwds):
      self.filtered_modules = kwds.get('filtered_modules',filtered_modules)
      super().__init__(*args, **kwds)

  def save(self, obj, save_persistent_id=True):
    self.framer.commit_frame()

    # Check for persistent id (defined by a subclass)
    pid = self.persistent_id(obj)
    if pid is not None and save_persistent_id:
      self.save_pers(pid)
      return

    # Check the memo
    x = self.memo.get(id(obj))
    if x is not None:
      self.write(self.get(x[0]))
      return

    # filter by module
    if obj.__module__ in self.filtered_modules:
      return self.filtered_modules[obj.__module__]

    rv = NotImplemented
    reduce = getattr(self, "reducer_override", None)
    if reduce is not None:
      rv = reduce(obj)

    if rv is NotImplemented:
      # Check the type dispatch table
      t = type(obj)
      f = self.dispatch.get(t)
      if f is not None:
        f(self, obj)  # Call unbound method with explicit self
        return

      # Check private dispatch table if any, or else
      # copyreg.dispatch_table
      reduce = getattr(self, 'dispatch_table', dispatch_table).get(t)
      if reduce is not None:
        rv = reduce(obj)
      else:
        # Check for a class with a custom metaclass; treat as regular
        # class
        if issubclass(t, type):
          self.save_global(obj)
          return

        # Check for a __reduce_ex__ method, fall back to __reduce__
        reduce = getattr(obj, "__reduce_ex__", None)
        if reduce is not None:
          rv = reduce(self.proto)
        else:
          reduce = getattr(obj, "__reduce__", None)
          if reduce is not None:
            rv = reduce()
          else:
            raise PicklingError("Can't pickle %r object: %r" %
                      (t.__name__, obj))

    # Check for string returned by reduce(), meaning "save as global"
    if isinstance(rv, str):
      self.save_global(obj, rv)
      return

    # Assert that reduce() returned a tuple
    if not isinstance(rv, tuple):
      raise PicklingError("%s must return string or tuple" % reduce)

    # Assert that it returned an appropriately sized tuple
    l = len(rv)
    if not (2 <= l <= 6):
      raise PicklingError("Tuple returned by %s must have "
                "two to six elements" % reduce)

    # Save the reduce() output and finally memoize the object
    self.save_reduce(obj=obj, *rv)


def filtered_dump(obj, file, protocol=None, byref=None, fmode=None, recurse=None):#, strictio=None):
    """pickle an object to a file"""
    from dill._dill import stack, _main_module
    from dill.settings import settings
    strictio = False #FIXME: strict=True needs cleanup
    if protocol is None: protocol = settings['protocol']
    if byref is None: byref = settings['byref']
    if fmode is None: fmode = settings['fmode']
    if recurse is None: recurse = settings['recurse']
    stack.clear()  # clear record of 'recursion-sensitive' pickled objects
    pik = FilteredPickler(file, protocol)
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
            StockPickler.save_global(pickler, obj)
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
    file = StringIO()
    filtered_dump(obj, file, protocol, byref, fmode, recurse)#, strictio)
    return file.getvalue()
