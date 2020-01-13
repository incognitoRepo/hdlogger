class StdDefTracer:

  def trace_dispatch(self, frame, event, arg):
    """this is the entry point for this class"""
    if not frame: sys.settrace(None); return None
    if not predicate(frame): sys.settrace(None); return None
    if filtered_function(frame.f_code.co_name):
      return None
    if filtered_filename(frame.f_code.co_filename):
      return None
    try:
      assert self.initialize(frame, event, arg) # ears1
    except:
      wf( stackprinter.format(sys.exc_info()),'logs/tracer.dispatch.log', 'a')
      raise

    if event == 'line':
      return self.dispatch_line(frame, arg)
    if event == 'call':
      return self.dispatch_call(frame, arg)
    if event == 'return':
      return self.dispatch_return(frame, arg)
    if event == 'exception':
      return self.dispatch_exception(frame, arg)
    if event == 'c_call':
      return self.trace_dispatch
    if event == 'c_exception':
      return self.trace_dispatch
    if event == 'c_return':
      return self.trace_dispatch
    print('bdb.Bdb.dispatch: unknown debugging event:', repr(event))
    return self.trace_dispatch
