from .classes import PickleableState

def make_pickleable_frame(frame):
  kwds = {
    "filename": frame.f_code.co_filename,
    "lineno": frame.f_lineno,
    "function": frame.f_code.co_name,
    "local_vars": frame.f_code.co_names,
    "code_context": getcodecontext(frame,frame.f_lineno)[0],
    "count": getcodecontext(frame,frame.f_lineno)[1],
  }
  return PickleableFrame(kwds)


def make_pickleable_state(state) -> PickleableState:
  kwds = {
      "frame": pickleable_dispatch(state.frame),
      "event": state.event,
      "arg": pickleable_dispatch(state.arg),
      "f_locals": pickleable_dispatch(state.frame.f_locals),
      "count": state.count,
      "function": state.function,
      "module": state.module,
      "format_filename": state.format_filename,
      "lineno": state.lineno,
      "stdlib": state.stdlib,
      "source": state.source,
    }
  try:
    pickleable_state = PickleableState(kwds)
  except:
    wf(stackprinter.format(sys.exc_info()),'logs/make_pickleable_state.log','a')
    raise SystemExit
  return pickleable_state
