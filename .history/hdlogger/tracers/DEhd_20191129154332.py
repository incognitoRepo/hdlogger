import sys, os, io, linecache, collections, inspect, threading, stackprinter, jsonpickle, copyreg, traceback
import pickle, dill
from itertools import count
from functools import singledispatchmethod, cached_property
from pathlib import Path
from typing import Callable, Iterable
from types import FunctionType, GeneratorType, FrameType
from bdb import BdbQuit
from hunter.const import SYS_PREFIX_PATHS
from pydantic import ValidationError
from inspect import CO_GENERATOR, CO_COROUTINE, CO_ASYNC_GENERATOR
from ..data_structures import TraceHookCallbackException, TraceHookCallbackReturn

GENERATOR_AND_COROUTINE_FLAGS = CO_GENERATOR | CO_COROUTINE | CO_ASYNC_GENERATOR # 672
WRITE = True
def ws(spaces=0,tabs=0):
  indent_size = spaces + (tabs * 2)
  whitespace_character = " "
  return f"{whitespace_character * indent_size}"

def _c(s,modifier=0,intensity=3,color=0):
  """
  mod      ::= 0(reset)|1(bold)|2(faint)|3(italic)|4(underline)
  int      ::= 9(intense fg) | 3(normal bg)
  clr      ::= 0(blk)|1(red)|2(grn)|3(ylw)|4(blu)|5(mag)|6(cyn)|7(wht)
  """
  escape = "\x1b["
  reset_modifier = 0
  ns = f"{escape}{modifier};{intensity}{color}m{s}{escape}{reset_modifier}m"
  return ns

def c(s,arg=None):
  if WRITE is True: return s
  """apply color to a string"""
  if s == 'call': return _c(s,modifier=1,intensity=9,color=2)
  if s == 'line': return _c(s,modifier=2,intensity=3,color=0)
  if s == 'return': return _c(s,modifier=1,intensity=9,color=3)
  if s == 'exception': return _c(s,modifier=1,intensity=9,color=1)

  if arg:
    if arg == 'vars': return _c(s,modifier=0,intensity=9,color=5)
    # symbols
    if arg == 'call': return _c(s,modifier=1,intensity=9,color=2)
    if arg == 'line': return _c(s,modifier=2,intensity=3,color=0)
    if arg == 'return': return _c(s,modifier=1,intensity=9,color=3)
    if arg == 'exception': return _c(s,modifier=1,intensity=9,color=1)

def write_file(obj,filename,mode='w'):
  with open(filename,mode) as f:
    f.write(obj)

def first_true(iterable, default=False, pred=None):
    """Returns the first true value in the iterable.

    If no true value is found, returns *default*

    If *pred* is not None, returns the first item
    for which pred(item) is true.

    """
    # first_true([a,b,c], x) --> a or b or c or x
    # first_true([a,b], x, f) --> a if f(a) else b if f(b) else x
    return next(filter(pred, iterable), default)

def pickle_exc_arg(exc_arg):
  try:
    kwds = dict(exc_arg)
    kwds['tb'] = traceback.format_tb(exc_arg[-1])
    return TraceHookCallbackException, (kwds,),
  except:
    with open('logs/pickle_exc_arg.log','w') as f: f.write(stackprinter.format(sys.exc_info()))
    raise SystemExit

def pickle_ret_arg(ret_arg):
  try:
    kwds = dict(ret_arg)
    kwds['return_value'] = repr(ret_arg)
    return TraceHookCallbackReturn, (kwds,),
  except:
    with open('logs/pickle_ret_arg.log','w') as f: f.write(stackprinter.format(sys.exc_info()))
    raise SystemExit

def pickle_generator(gen):
  kwds = {
    'state': inspect.getgeneratorstate(gen),
    'locals': inspect.getgeneratorlocals(gen),
    'id': hex(id(gen))
  }
  return unpickle, (kwds,)

def pickle_frame(frame):
  kwds = {'f_fileno':frame.f_lineno}
  return unpickle, (kwds,)

def unpickle(kwds):
  Unpickleable = type('Unpickleable',(), dict.fromkeys(kwds))
  return Unpickeable(**kwds)


class State:
  SYS_PREFIX_PATHS = set((
    sys.prefix,
    sys.exec_prefix,
    os.path.dirname(os.__file__),
    os.path.dirname(collections.__file__),
  ))
  counter = count(0)

  def __init__(self, frame, event, arg):
    with open('logs/state.arg.log','a') as f: f.write(repr(arg)+"\n")
    self.frame = frame
    self.event = event
    self.arg = arg if arg else ""
    self.index = next(State.counter)
    self.initialize()

  def initialize(self):
    self.locals = self.frame.f_locals
    self.globals = self.frame.f_globals
    self.function = self.frame.f_code.co_name
    self.function_object = self.frame.f_code
    self.module = self.frame.f_globals.get('__name__','')
    self.filename = self.frame.f_code.co_filename
    self.lineno = self.frame.f_lineno
    self.code = self.frame.f_code
    self.stdlib = True if self.filename.startswith(SYS_PREFIX_PATHS) else False
    self.source = linecache.getline(self.filename, self.lineno, self.frame.f_globals)
    self.stack = []
    self._call = None
    self._line = None
    self._return = None
    self._exception = None
    self.initialize_copyreg()
    self.serialized_arg = self.serialize_arg()

  def initialize_copyreg(self):
    special_cases = [(GeneratorType,pickle_generator),
    (FrameType,pickle_frame),]
    for special_case in special_cases:
      copyreg.pickle(*special_case)

    if self.event == "return":
      self.narg = TraceHookCallbackReturn(**{'return_value':self.arg})
    if self.event == "exception":
      self.narg = TraceHookCallbackException(**dict(zip(['etype','value','tb'],self.arg)))

  def serialize_arg(self):
    try:
      _as_bytes = pickle.dumps(self.arg) if not getattr(self,'narg',None) else pickle.dumps(self.narg)
    except:
      with open('logs/serialize_arg.err.log','a') as f: f.write(stackprinter.format(sys.exc_info())+"\n\n"+stackprinter.format())
      raise
    _as_hex = _as_bytes.hex()
    with open('logs/state.serialize_arg.log','a') as f: f.write(_as_hex)
    return _as_hex

  def deserialize_arbitrary_pyobj(self,serialized_pyobj):
    def _deserialize(hexo):
      b = bytes.fromhex(hexo)
      deserialized = dill.loads(b)
      with open('logs/state.deserialized.log','a') as f: f.write(str(deserialized))
      return deserialized
    if isinstance(serialized_pyobj,bytes):
      deserialized = _deserialize(b)
      return deserialized
    elif isinstance(serialized_pyobj,Iterable):
      deserialized = [_deserialize(obj) for obj in serialized_pyobj]
      return deserialized
    else:
      raise SystemExit(f'cannot deserialize {serialized_pyobj}')

  def serialize_arbitrary_pyobj(self,pyobj):
    _as_bytes = dill.dumps(pyobj)
    serialized = _as_bytes.hex()
    with open('state.serialized.log','a') as f: f.write(serialized)
    return serialized


  @cached_property
  def format_filename(self):
    if not isinstance(self.filename,Path):
      filename = Path(self.filename)
    stem = f"{filename.stem:>10.10}"
    return stem

  @property
  def format_call(self):
    self.stack.append(f"{self.module}.{self.function}")
    if self._call:
      return self._call
    try:
      sub_s = ", ".join(self.arg)
    except:
      with open('logs/format_call.log','a') as f: f.write(self.arg)
      raise SystemExit()
    s = (
      f"{self.index:>5}|{self.format_filename}:{self.lineno:<5}{c(self.event):9} "
      f"{ws(spaces=len(self.stack) - 1)}{c('=>',arg='call')} "
      f"{self.function}({sub_s})\n"
    )
    self._call = s
    # TODO: this is a perfect place for logging.debug()

    return s

  @property
  def format_line(self):
    if self._line:
      return self._line
    s = (
      f"{self.index:>5}|{self.format_filename}:{self.lineno:<5}{c(self.event):9} "
      f"{ws(spaces=len(self.stack))}{c('  ',arg='line')} "
      f"{self.source}\n"
    )
    self._line = s
    return s

  @property
  def format_return(self):
    if self._return:
      return self._return
    s = (
      f"{self.index:>5}|{self.format_filename}:{self.lineno:<5}{c(self.event):9} "
      f"{ws(spaces=len(self.stack) - 1)}{c('<=',arg='return')} "
      f"{self.function}: {self.arg}"
    )
    self._return = s
    if self.stack and self.stack[-1] == f"{self.module}.{self.function}":
      self.stack.pop()
    return s

  @property
  def format_exception(self):
    if self._return:
      return self._return
    s = (
      f"{self.index:>5}|{self.format_filename}:{self.lineno:<5}{c(self.event):9} "
      f"{ws(spaces=len(self.stack) - 1)}{c(' !',arg='call')} "
      f"{self.function}: {self.arg}"
    )
    self._return = s
    return s


class HiDefTracer:

  def __init__(self):
    self.state = None
    self.return_values = []
    self.serialized_data = []

  def trace_dispatch(self, frame, event, arg):
    with open('logs/hdlog.arg.log','a') as f: f.write(repr(arg)+'\n')
    self.state = State(frame,event,arg)
    # if self.quitting:
      # return # None
    if event == 'line':
      return self.dispatch_line(frame)
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

  def dispatch_call(self, frame, arg):
    self.user_call(frame, arg)
    return self.trace_dispatch

  def dispatch_line(self, frame):
    self.user_line(frame)
    return self.trace_dispatch

  def dispatch_return(self, frame, arg):
    """note: there are a few `special cases` wrt `arg`"""
    if arg is not None:
      try:
        with open('logs/dispatch_return.log','a') as f: f.write(str(arg))
        kwds = {'return_value': arg}
        TraceHookCallbackReturn(**kwds)
      except ValidationError as e:
        print(e.json())
        raise
      except:
        print(stackprinter.format(sys.exc_info()))
        raise
    # if isinstance(arg,GeneratorType):
    #   g_state = inspect.getgeneratorstate(arg)
    #   g_locals = inspect.getgeneratorlocals(arg)
    #   arg = f"<generator object: state:{g_state.lower()} locals:{g_locals} id:{hex(id(self._arg))}>"
    self.user_return(frame, arg)
    return self.trace_dispatch

  def dispatch_exception(self, frame, arg):
    if arg is not None:
      try:
        with open('logs/dispatch_exception.log','a') as f: f.write(str(arg))
        kwds = dict(zip(['etype','value','traceback'],arg))
        exc_info = TraceHookCallbackException(**kwds)
      except ValidationError as e:
        print(e.json())
        raise
      except:
        print(stackprinter.format(sys.exc_info()))
        raise
    self.user_exception(frame, arg)
    return self.trace_dispatch

  def deserialize(self,serialized_objs):
    """Load each item that was previously written to disk."""
    l = []
    for obj_as_hex in serialized_objs:
      pickled_obj = bytes.fromhex(obj_as_hex)
      deserialized = pickle.loads(pickled_obj)
      l.append(deserialized)
    return l

  def serialize(self,obj):
    class FakeFrame:
      def __init__(self):
        self.f_lineno = None

    def pickle_frame(frame):
      # return f"{frame.f_lineno}"
      return FakeFrame, (), {'f_lineno':2}

    # b = io.BytesIO()
    # p = pickle.Pickler(b)
    # p.dispatch_table = copyreg.dispatch_table.copy()
    # p.dispatch_table[FrameType] = pickle_frame
    # p.dump(obj)
    # pickled_bytes = b.getvalue()
    # pickled_bytes_as_hex = pickled_bytes.hex()
    with open('logs/f.getvalue.log','w') as f:
      f.write(pickled_bytes_as_hex)
    self.serialized_data.append(pickled_bytes_as_hex)

  def user_call(self, frame, argument_list):
    print('user_call')
    print(self.state.format_call)
    return self.trace_dispatch

  def user_line(self, frame):
    print('user_line')
    print(self.state.format_line)
    return self.trace_dispatch

  def user_return_no_generator(self, frame, return_value):
    print('user_return_no_generator')
    print("__return__1" + getattr(frame.f_locals,'__return__','dne'))
    print(self.state.format_return)
    frame.f_locals['__return__'] = return_value
    print("__return__2" + getattr(frame.f_locals,'__return__','dne'))

  def user_return_f_locals(self, frame, return_value):
    print('user_return_f_locals')
    arg = frame.f_locals['rv']
    print("arg:\n" + "\n".join([repr(elm) for elm in arg]))
    print("__return__1" + getattr(frame.f_locals,'__return__','dne'))
    print(self.state.format_return)
    frame.f_locals['__return__'] = return_value
    frame.f_locals['rv'] = [123]
    print("__return__2" + getattr(frame.f_locals,'__return__','dne'))

  def user_return_w_inspect(self, frame, return_value):
    print('user_return_w_inspect')
    arg = frame.f_locals['rv']
    print(f"{inspect.getgeneratorstate(return_value)}")
    print(f"{inspect.getgeneratorlocals(return_value)}")
    print("__return__1" + getattr(frame.f_locals,'__return__','dne'))
    print(self.state.format_return)
    frame.f_locals['__return__'] = return_value
    frame.f_locals['rv'] = [123]
    print("__return__2" + getattr(frame.f_locals,'__return__','dne'))

  def user_return_w_jsonpickle(self, frame, return_value):
    # TODO
    pass

  def user_return_w_itertools_tee(self, frame, return_value):
    # TODO
    pass

  def user_return(self, frame, return_value):
    print('user_return')
    print(self.state.format_return)
    if return_value:
      assert self.state.arg == return_value, f"{self.state.arg=}, {return_value=}"
      self.return_values.append(return_value)

  def user_exception(self, frame, exc_info):
    print('user_exception')
    print(self.state.format_exception)
    return self.trace_dispatch

  def bp_commands(self, frame):
    # self.currentbp is set in bdb in Bdb.break_here if a breakpoint was hit
    if getattr(self, "currentbp", False) and \
               self.currentbp in self.commands:
      currentbp = self.currentbp
      self.currentbp = 0
      lastcmd_back = self.lastcmd
      self.setup(frame, None)
      for line in self.commands[currentbp]:
        self.onecmd(line)
      self.lastcmd = lastcmd_back
      if not self.commands_silent[currentbp]:
        self.print_stack_entry(self.stack[self.curindex])
      if self.commands_doprompt[currentbp]:
        self._cmdloop()
      self.forget()
      return
    return 1


  def globaltrace_lt(self, frame, why, arg):
    if why == 'call':
      code = frame.f_code
      filename = frame.f_globals.get('__file__', None)
      if filename:
        # XXX _modname() doesn't work right for packages, so
        # the ignore support won't work right for packages
        modulename = _modname(filename)
        if modulename is not None:
          ignore_it = self.ignore.names(filename, modulename)
          if not ignore_it:
            if self.trace:
              print((" --- modulename: %s, funcname: %s" % (modulename, code.co_name)))
            return self.localtrace
      else:
        return None

  @singledispatchmethod
  def run(self, cmd, *args, **kwds):
    raise NotImplementedError

  @run.register
  def _(self, cmd:str, *args, **kwds):
    globals, locals = kwds.get('globals',None), kwds.get('locals',None)
    if globals is None:
      import __main__
      globals = __main__.__dict__
    if locals is None:
      locals = globals
    self.reset()
    if isinstance(cmd, str):
      cmd = compile(cmd, "<string>", "exec")
    sys.settrace(self.trace_dispatch)
    try:
      exec(obj:=compile(cmd, "<string>", "exec"), globals, locals) # no return value
      return eval(expr:=compile(cmd, "<string>", "eval"), globals, locals) # returns single expression
    except BdbQuit:
      pass
    finally:
      self.quitting = True
      sys.settrace(None)

  @run.register
  def _(self, cmd:FunctionType, *args, **kwds):

    self.reset()
    sys.settrace(self.trace_dispatch)
    res = None
    try:
      res = cmd(**kwds)
      self.return_value = res
    except BdbQuit:
      pass
    finally:
      self.quitting = True
      sys.settrace(None)
    return res

  def reset(self):
    """Set values of attributes as ready to start debugging."""
    import linecache
    linecache.checkcache()
    self.botframe = None
    # self._set_stopinfo(None, None)


def main():
  from tester.helpers import final_selector
  t = HiDefTracer()
  t.run(final_selector)


if __name__ == '__main__':
  main()



