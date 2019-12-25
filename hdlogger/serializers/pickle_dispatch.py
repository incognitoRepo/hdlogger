import optparse, copyreg, inspect, os, ctypes

import stackprinter, sys, jsonpickle
import dill as pickle

from typing import Iterable, Iterator, Mapping, Sequence, Collection, Callable
from types import GeneratorType, FrameType, TracebackType, FunctionType

from hdlogger.utils import *

from .classes import State, PickleableFrame, PickleableTraceback, PickleableOptparseOption
from .picklers import TryUntilPickleable

FUNCS = [
  lambda v: pickle.loads(pickle.dumps(v)),
  lambda v: jsonpickle.encode(v),
  lambda v: repr(v),
  lambda v: getattr(v,'__class__.__name__')
]

def initialize_copyreg(Type2Add=None):
  pickle.load_types()
  special_cases = [
    (GeneratorType, pickle_generator),
    (FrameType, pickle_frame),
    (TracebackType, pickle_traceback),
    (optparse.Option, pickle_optparse_option),
    (State, pickle_state),
    (FunctionType, pickle_function),
    (os._Environ, pickle_environ),
    (ctypes.CDLL, pickle_ctypes),
    (ctypes.create_string_buffer(10)._type_, pickle_ctypes_array),
    (Mapping, pickleable_dict),
  ]
  if Type2Add:
    special_cases.append((Type2Add, pickle_dynamically_added_as_repr))
  for special_case in special_cases:
    copyreg.pickle(*special_case)

def pickleable_dispatch(arg):
  """dispatch for ensuring `arg`
  (which is passed to sys.settrace) is pickleable.
  ..arg: Any
  """
  try:
    return pickle.loads(pickle.dumps(arg))
  except:
    if isinstance(arg, bytes):
      return str(arg)
    if isinstance(arg, str):
      return arg
    if isinstance(arg,Mapping):
      return pickleable_dict(arg)
    NonStrIterable = lambda arg: isinstance(arg,Iterable) and not isinstance(arg,str)
    if NonStrIterable(arg):
      return pickleable_list(arg)
    if isinstance(arg,FrameType):
      return pickleable_frame(arg)
    else:
      return pickleable_simple(arg)

def pickleable_environ(env):
  envd = dict(env)
  try:
    return pickleable_dict(envd)
  except:
    wf( stackprinter.format(sys.exc_info()),'logs/pickleable_env.tracer.log', 'a')
    raise

def pickleable_frame(frm):
  try:
    return pickle.loads(pickle.dumps(frm))
  except:
    wf('logs/pickleable_frame.tracer.log', stackprinter.format(sys.exc_info()))
    raise

def pickleable_dict(d):
  funcs = [
    lambda v: pickle.loads(pickle.dumps(v)),
    lambda v: jsonpickle.encode(v),
    lambda v: getattr(v,'__class__.__name__')
  ]
  tup = TryUntilPickleable(funcs,d.values())
  rvl = tup.try_until()
  rvl = [rvl] if not isinstance(rvl,list) else rvl
  nkwds = {}
  try:
    for k,v in zip(d.keys(),rvl):
      if (
        k == 'builtins'
        or k.startswith('_')
      ): continue
      else:
        nkwds.update({k:v})
    return nkwds
  except:
    wf(stackprinter.format(sys.exc_info()),'logs/pickle_dispatcch.pickleable_dict.error.log','a')
    raise

def pickleable_globals(g):
  cp = g.copy()
  cp['__builtins__'] = "-removed-"
  g2 = pickleable_dict(cp)
  return g2

def pickleable_list(l):
  if l == "": return ""
  try:
    ddl = pickle.dumps(l)
    assert pickle.loads(ddl)
    return l
  except:
      l2 = []
      for elm in l:
        try:
          dde = pickle.dumps(elm)
          assert pickle.loads(dde), f"cant load pickle.dumps(dde)={dde}"
          l2.append(dde)
        except:
          for test in [
            lambda: pickle.dumps(jsonpickle.encode(elm)),
            lambda: pickle.dumps(repr(elm)),
            lambda: pickle.dumps(str(elm)),
            lambda: pickle.dumps(elm.__class__.__name__)
            ]:
            try:
              dde = test()
              assert pickle.loads(dde), f"cant load pickle.dumps(dde)={dde}"
              l2.append(dde)
            except: pass
          wf( stackprinter.format(sys.exc_info()),'logs/models.unpickleable.log', 'a')
          raise
      return l2

def pickleable_simple(s):
  if s == "": return ""
  try:
    dds = pickle.dumps(s)
    assert pickle.loads(dds)
    return s
  except:
    for test in [
      lambda: pickle.dumps(jsonpickle.encode(s)),
      lambda: pickle.dumps(repr(s)),
      lambda: pickle.dumps(str(s)),
      lambda: pickle.dumps(s.__class__.__name__)
      ]:
      try:
        dds = test()
        assert pickle.loads(dds), f"cant load pickle.dumps(dds)={dds}"
        return dds
      except:
        pass
    wf( stackprinter.format(sys.exc_info()),'logs/models.unpickleable.log', 'a')
    raise

# ===-===-===-===-===-
# def __reduce__():
#   a:Callable
#   b:tuple # args for Callable
#   c:state # passed to obj's __setstate__()
#   d:Iterator # List-like, obj.append(item) | obj.append(list_of_items)
#   e:Iterator # Dict-like, obj[key]=value
#   f:Callable # (obj,state) signature

def copyreg_pickle(type,function,constructor=None):
  '''_function_ should be used as a "reduction" for _type_ objs
  function: returns Union[str,tuple(2 or 3 elements)]
  constructor: Callable: reconstruct the object when called with args from _function_
  '''
  pass

def pickle_dynamically_added_as_repr(dynobj):
  string = repr(dynobj)
  return unpickle_dynamically_added_as_repr, (string,)

def unpickle_dynamically_added_as_repr(string):
  return string

def pickle_ctypes_array(arr):
  string = repr(arr)
  return unpickle_ctypes_array, (string,)

def unpickle_ctypes_array(string):
  return string

def pickle_ctypes(obj):
  """obj = ctypes.create_string_buffer(1)
    obj._type_ = ctypes.c_char
    type(obj) = ctypes.c_char_Array_1
  """
  kwds={}
  if isinstance(obj, ctypes.Array):
    kwds = {'cls':obj._type_,'wrapper':obj._wrapper,'length':obj._length_}
    return unpickle_ctypes, (kwds,)
  elif isinstance(obj,ctypes.CDLL):
    kwds = {'cls':obj.__class__,'dllpath':obj._name}
    return unpickle_ctypes, (kwds,)
  else:
    kwds = {'cls':type(obj),'wrapper':obj._wrapper,'length':None}
    return unpickle_ctypes, (kwds,)

def unpickle_ctypes(kwds):
  if kwds['cls'] == ctypes.CDLL:
    # return kwds['cls'](kwds['dllpath'])
    return 1
  elif kwds['cls'] == ctypes.c_char:
    # return kwds['cls']*kwds['length']
    return 2
  else:
    assert kwds['length'] is None, f"{kwds['length']}"
    # type_,wrapper,length = kwds.values()
    # if length is not None:
    #   type_ = type_ * length
    # obj = type_.from_address(wrapper.get_address())
    # obj._wrapper = wrapper
    # return obj
    return 3

def pickle_environ(e):
  kwds = e.__dict__.copy()
  kwds['data'] = kwds.pop('_data')
  return unpickle_environ, (kwds,)

def unpickle_environ(kwds):
  return os._Environ

def pickle_function(fnc):
  sig = inspect.signature(fnc)
  inspect.Signature(sig.parameters.values())
  kwds = sig.parameters
  return unpickle_function, (kwds,)

def unpickle_function(kwds):
  return inspect.Signature(kwds)

def pickle_frame(frame):
  kwds = {
    "filename": frame.f_code.co_filename,
    "lineno": frame.f_lineno,
    "function": frame.f_code.co_name,
    "local_vars": frame.f_code.co_names,
    "code_context": getcodecontext(frame,frame.f_lineno)[0],
    "count": getcodecontext(frame,frame.f_lineno)[1],
    "f_code": frame.f_code
  }
  return unpickle_frame, (kwds,)

def unpickle_frame(kwds):
  return PickleableFrame(kwds)

def pickle_state(st):
  kwds = {
      "frame": st.pickleable_frame,
      "event": st.event,
      "arg": st.pickleable_arg,
      "locals": st.pickleable_locals,
      "count": st.count,
      "function": st.function,
      "module": st.module,
      "filename": st.filename,
      "lineno": st.lineno,
      "stdlib": st.stdlib,
      "source": st.source,
      "format_filename": st.format_filename,
      "stack": st.stack,
  }
  return unpickle_state, (kwds,)

def unpickle_state(kwds):
  return PickleableState(**kwds)

def pickle_generator(gen):
  kwds = {
    'state': inspect.getgeneratorstate(gen),
    'f_locals': inspect.getgeneratorlocals(gen),
    'pid': hex(id(gen))
  }
  return unpickle_generator, (kwds,)

def unpickle_generator(kwds):
  return PickleableGenerator(**kwds)

def getcodecontext(frame,lineno,context=2):
  if context > 0:
    start = lineno - 1 - context//2
    try:
      lines, lnum = inspect.findsource(frame)
    except OSError:
      lines = count = None
    else:
      start = max(0, min(start, len(lines) - context))
      lines = lines[start:start+context]
      count = lineno - 1 - start
  else:
    lines = count = None
  return lines, count

def pickle_traceback(tb):
  kwds = {
    'lasti': tb.tb_lasti,
    'lineno':tb.tb_lineno,
  }
  return unpickle_traceback, (kwds,)

def unpickle_traceback(kwds):
  return PickleableTraceback(**kwds)

def pickle_optparse_option(optopt):
  """str(pickle.loads(pickle.dumps(self)))"""
  kwds = {
    'module':optopt.__module__,
    'classname':optopt.__class__.__name__,
  }
  return unpickle_optparse_option, (kwds,)

def unpickle_optparse_option(kwds):
  return PickleableOptparseOption(**kwds)
