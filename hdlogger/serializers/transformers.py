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
  kwds = {
      "frame": pickle.loads(pickle.dumps(state.frame)),
      "event": state.event,
      "arg": pickle.loads(pickle.dumps(pickleable_dispatch(state.arg))), # ears3
      "callargs": pickle.loads(pickle.dumps(pickleable_dispatch(state.callargs))),
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
  assert pickle.loads(pickle.dumps(kwds)) # so the problem is in TryUntilPickleable
  pickleable_state = PickleableState(kwds)
  try:
    pickle.loads(pickle.dumps(kwds))
  except:
    wf(stackprinter.format(sys.exc_info()),'logs/make_pickleable_state.error.log','a')
    raise
  else:
    return pickleable_state

