import stackprinter, inspect, sys
import dill as pickle
from dill._dill import dumps_with_custom_pickler
from prettyprinter import pformat
from .classes import PickleableState, PickleableFrame
from .pickle_dispatch import pickleable_dispatch, FUNCS, pickleable_dict
from hdlogger.serializers.picklers import TryUntilPickleable, FilteredPickler
from hdlogger.utils import *

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

def make_pickleable_frame(frame):
  kwds = {
    "filename": frame.f_code.co_filename,
    "lineno": frame.f_lineno,
    "function": frame.f_code.co_name,
    "local_vars": frame.f_code.co_names,
    "code_context": getcodecontext(frame,frame.f_lineno)[0],
    "count": getcodecontext(frame,frame.f_lineno)[1],
    "f_code": frame.f_code
  }
  return PickleableFrame(kwds)

def make_pickleable_state(state,stack) -> PickleableState:
  funcs = FUNCS
  assert isinstance(state.lineno,int), f"{state.lineno=}"
  assert isinstance(state.st_count,int), f"{state.st_count=}"
  # try:
  #   fls = state.frame.f_locals; assert isinstance(fls,dict)
  #   a=pickleable_dict(state.frame.f_locals)
  #   wf(f"{a=}",'logs/transformers.make_pklbl_st.log','a')
  #   wf('\n'.join([f"{k}: {v}" for k,v in state.frame.f_locals.items()]),'logs/transformers.make_pklbl_st.log','a')
  #   b=pickle.loads(a)
  # except:
  #   wf(stackprinter.format(sys.exc_info()),'logs/filtered_dumps.log','a')
  #   raise
  kwds = {
      "frame": pickle.loads(pickle.dumps(state.frame)),
      "event": state.event,
      "arg": pickle.loads(pickle.dumps(pickleable_dispatch(state.arg))),
      # "f_locals": pickle.loads(dumps_with_custom_pickler(state.frame.f_locals)),
      "f_locals": pickle.loads(pickle.dumps(pickleable_dict(state.frame.f_locals))),
      "st_count": state.st_count,
      "function": state.function,
      "module": state.module,
      "format_filename": state.format_filename,
      "lineno": state.lineno,
      "stdlib": state.stdlib,
      "source": state.source,
      "stack": [elm for elm in PickleableState._stack]
    }
  # wf(pformat(kwds),'logs/make_pklbl_st.log','a')
  assert pickle.loads(pickle.dumps(kwds)) # so the problem is in TryUntilPickleable
  try:
    tup = TryUntilPickleable(funcs=funcs,arg=kwds.values())
    rvl = [tup.try_until()] if not isinstance(tup.try_until(),list) else tup.try_until()
    nkwds = {}
    for k,v in zip(kwds.keys(),rvl):
      if (
        k == 'builtins'
        or k.startswith('_')
      ): continue
      else:
        nkwds.update({k:v})
    # wf(pformat(nkwds),'logs/make_pickleable_state.debug.log','a')
    pickleable_state = PickleableState(nkwds)
  except:
    wf(stackprinter.format(sys.exc_info()),'logs/make_pickleable_state.error.log','a')
    raise
  return pickleable_state

