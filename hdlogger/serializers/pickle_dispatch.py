import optparse, copyreg, inspect

import stackprinter, sys
import dill as pickle

from typing import Iterable, Mapping, Sequence
from types import GeneratorType, FrameType, TracebackType, FunctionType

from hdlogger.utils import *

from .classes import State, PickleableFrame, PickleableTraceback, PickleableOptparseOption

def initialize_copyreg():
  special_cases = [
    (GeneratorType, pickle_generator),
    (FrameType, pickle_frame),
    (TracebackType, pickle_traceback),
    (optparse.Option, pickle_optparse_option),
    (State, pickle_state),
    (FunctionType, pickle_function),
    # (Mapping, pickleable_dict)
  ]
  for special_case in special_cases:
    copyreg.pickle(*special_case)

def pickleable_dispatch(obj):
  try:
    return pickle.loads(pickle.dumps(obj))
  except:
    if isinstance(obj, bytes): obj = str(obj)
    if isinstance(obj,Iterable) and not isinstance(obj,str):
      if isinstance(obj, Mapping):
        return pickleable_dict(obj)
      elif isinstance(obj, Sequence):
        return pickleable_list(obj)
      else:
        wf(stackprinter.format(sys.exc_info()),'logs/models.pickleable_dispatch.log','a')
        raise
    elif isinstance(obj,FrameType):
      return pickleable_frame(obj)
    else:
      return pickleable_simple(obj)
    s = stackprinter.format(sys.exc_info())
    print(s)
    raise SystemExit(f"failure in pickleable_dispatch: cannot pickle {obj}")

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
  funclist = [
    lambda v: pickle.loads(pickle.dumps(v)),
    lambda v: jsonpickle.encode(v),
    lambda v: getattr(v,'__class__.__name__')
  ]
  d2 = {}
  for k,v in d.items():
    try:
      checked = checkfuncs(funclist,v)
      pickleable = next(filter(None,checked))
      d2[k] = pickleable
    except:
      s = stackprinter.format(sys.exc_info())
      wf( s,'logs/pickleable_dict.tracers.log',mode="a")
      wf((
        f"unable to pickle {d} due to:\n{k=}\n{v=}"
        f"{isinstance(v,GeneratorType)=}\n{pickle.loads(pickle.dumps(v))}"
      ),"a")
      raise SystemExit(
        f"unable to pickle {d} due to:\n{k=}\n{v=}"
        f"{isinstance(v,GeneratorType)=}\n{pickle.loads(pickle.dumps(v))}"
      )
  return d2

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
          raise SystemExit
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
    raise SystemExit

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
