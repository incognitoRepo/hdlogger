import sys, os, linecache, collections, inspect, threading
from functools import singledispatchmethod, cached_property
from pathlib import Path
from typing import Callable
from types import FunctionType, GeneratorType
from bdb import BdbQuit
from hunter.const import SYS_PREFIX_PATHS
from inspect import CO_GENERATOR, CO_COROUTINE, CO_ASYNC_GENERATOR

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

class State:
  SYS_PREFIX_PATHS = set((
    sys.prefix,
    sys.exec_prefix,
    os.path.dirname(os.__file__),
    os.path.dirname(collections.__file__),
  ))

  def __init__(self, frame, event, arg):
    self.frame = frame
    self.event = event
    self._arg = arg
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

  @property
  def arg(self):
    if isinstance(self._arg,GeneratorType):
      g_state = inspect.getgeneratorstate(self._arg)
      g_locals = inspect.getgeneratorlocals(self._arg)
      s = f"<generator object: state:{g_state.lower()} locals:{g_locals} id:{hex(id(self._arg))}>"
      return s
    return self._arg

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
    hunter_args = self.frame.f_code.co_varnames[:self.frame.f_code.co_argcount]
    fmtmap = lambda var: f"{c(var,'vars')}={repr(self.frame.f_locals.get(var, 'MISSING'))}"
    try:
      sub_s = ", ".join([fmtmap(var) for var in hunter_args])
    except:
      with open('format_call.log','a') as f:
        f.write(
          f"\n{hunter_args=}\n{self.frame.f_locals.keys()=}\n"
        )
      sub_s = ', '.join([type(var).__name__ for var in hunter_args])
    s = (
      f"{self.format_filename}:{self.lineno:<5}{c(self.event):9} "
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
      f"{self.format_filename}:{self.lineno:<5}{c(self.event):9} "
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
      f"{self.format_filename}:{self.lineno:<5}{c(self.event):9} "
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
      f"{self.format_filename}:{self.lineno:<5}{c(self.event):9} "
      f"{ws(spaces=len(self.stack) - 1)}{c(' !',arg='call')} "
      f"{self.function}: {self.arg}"
    )
    self._return = s
    return s


class HiDefTracer:

  def __init__(self):
    self.state = None
    self.return_values = type('return_values',(),{'pkl_values':[],'jpkl_values':[]})

  def trace_dispatch(self, frame, event, arg):
    print(f"{frame.f_code.co_flags=}, {frame.f_code.co_flags & GENERATOR_AND_COROUTINE_FLAGS}")
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
    self.user_return(frame, arg)
    return self.trace_dispatch

  def dispatch_exception(self, frame, arg):
    self.user_exception(frame, arg)
    return self.trace_dispatch

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
    import pickle, jsonpickle
    user_return.counter += 0
    try:
      pkl = pickle.dumps(return_value)
      self.return_values.pkl_values.append(pkl)
    except:
      jpkl = jsonpickle.encode(return_value)
      self.return_values.jpkl_values.append(jpkl)

    def main(arg) -> bool:
      try:
        if not arg or arg == None:
          pkld = Pkl(pickle.dumps(arg),pickle.dumps(None),h_idx)
          return_value = write_to_disk(pkld,debug=True)
          return return_value
        og_arg = arg
        # cleaned_arg = make_event_arg_pickleable(arg)
        pkld = get_pickled_bytes(arg,h_idx)
        return_value = write_to_disk(pkld,og_arg,debug=True)
        return return_value
      except:
        with open('hc843.log','a') as f:
          f.write(stackprinter.format())
          f.write(f"\n{arg}")
        raise SystemExit

    def make_event_arg_pickleable(arg,keep=False):
      if isinstance(arg,tuple) and isinstance(arg[1],BaseException):
        assert arg[2] is None or isinstance(arg[2],TracebackType), f"{info(arg)}"
        try:
          arg = traceback.format_exception_only(arg[0],arg[1])
        except:
          return arg
      elif isinstance(arg,addinfourl):
        arg = auto_repr(arg)
      elif isinstance(arg,OptionParser):
        try:
          _ = arg.option_list
          def nodctrepr(v): return repr(v) if not isinstance(v,dict) else repr(v.keys())
          arg = [nodctrepr(elm) for elm in _]
        except:
          with open('hc860.log','a') as f:
            f.write("\n".join(arg))
          raise SystemExit
      else:
        arg = arg
      return arg

    def get_pickled_bytes(cleaned_arg,h_idx):
      arg = cleaned_arg
      try:
        pre_pkld = Pkl(pickle.dumps(arg), type(arg), h_idx)
        return pre_pkld
      except pickle.PickleError as err:
        if isinstance(arg,tuple) and isinstance(arg[1],BaseException):
          assert arg[2] is None or isinstance(arg[2],TracebackType), f"{info(arg)}"
          try:
            arg = traceback.format_exception_only(arg[0],arg[1])
          except:
            return arg
        elif isinstance(arg,addinfourl):
          arg = auto_repr(arg)
        elif isinstance(arg,OptionParser):
          try:
            _ = arg.option_list
            def nodctrepr(v): return repr(v) if not isinstance(v,dict) else repr(v.keys())
            arg = [nodctrepr(elm) for elm in _]
          except:
            with open('hc902_err.log','a') as f:
              f.write("\n".join(arg))
            raise SystemExit
        if is_class(arg) or is_instance(arg):
          try:
            arg = auto_repr(arg)
            pre_pkld = Pkl(pickle.dumps(arg), type(arg), h_idx)
            return pre_pkld
          except:
            with open('hc879.log','a') as f:
              f.write(stackprinter.format(sys.exc_info()))
            raise SystemExit
        elif isinstance(arg,list):
          _ = [self.write_to_pickle(elm) for elm in arg]
          pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
          return pre_pkld
        elif has_dct(arg):
          _ = has_dct(arg)
          pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
          return pre_pkld
        else:
          with open('hc906_err.log','a') as f:
            f.write(stackprinter.format())
            f.write(repr(arg))
          raise SystemExit
      except AttributeError as err:
        if isinstance(arg,tuple):
          try:
            _ = [self.write_to_pickle(elm) for elm in arg]
            pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
            return pre_pkld
          except:
            with open('hc899','a') as f:
              f.write(stackprinter.format())
              f.write(repr(arg))
            raise SystemExit
        elif is_class(arg):
          arg = auto_repr(arg)
          pre_pkld = Pkl(pickle.dumps(arg), type(arg), h_idx)
          return pre_pkld
        elif is_instance(arg):
          arg = auto_repr(arg)
          pre_pkld = Pkl(pickle.dumps(arg), type(arg), h_idx)
          return pre_pkld
        elif isinstance(arg,dict):
          try:
            lst = []
            for k,v in arg.items():
              lst.append(f"{k}: {get_pickled_bytes(v)}")
            _ = "\n".join(lst)
            pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
            return pre_pkld
          except:
            print("AttributeError Unresolved 2")
        elif inspect.isfunction(arg):
          try:
            _ = is_function(arg)
            pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
            return pre_pkld
          except:
            print("AttributeError Unresolved 4")
            raise SystemExit
        elif isinstance(arg,list):
          _ = [self.write_to_pickle(elm) for elm in arg]
          pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
          return pre_pkld
        else:
          with open('hc952_err.log','a') as f:
            f.write(stackprinter.format())
            f.write(repr(arg))
          raise SystemExit
      except TypeError as err:
        if isinstance(arg,tuple):
          if is_class(arg[0]):
            _ = auto_repr(arg[0])
            pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
            return pre_pkld
          else:
            debug_error(arg,auto_repr(arg[0]),"TypeError")
            print("TypeError Unresolved 1")
            raise SystemExit
        elif isinstance(arg,dict):
          try:
            lst = []
            for k,v in arg.items():
              lst.append(f"{k}: {get_pickled_bytes(v)}")
            _ = "\n".join(lst)
            pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
            return pre_pkld
          except:
            print("TypeError Unresolved 2")
            raise SystemExit
        elif hasattr(arg,'__dict__'):
          try:
            d = arg.__dict__
            print(d)
            lst = []
            for k,v in d.items():
              lst.append(f"{k}: {repr(v)}")
            _ = "\n".join(lst)
            pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
            return pre_pkld
          except:
            print("TypeError Unresolved 3")
            raise SystemExit
        elif isinstance(arg,GeneratorType):
          try:
            _ = repr(list(arg))
            pre_pkld = Pkl(pickle.dumps(_), type(_), h_idx)
            return pre_pkld
          except:
            print("TypeError Unresolved 4")
            raise SystemExit
        else:
          with open('hc999_err.log','a') as f:
            f.write(stackprinter.format())
            f.write(repr(arg))
          raise SystemExit
      except:
        with open('hc1004_err.log','a') as f:
          f.write(stackprinter.format())
          f.write(repr(arg))
        raise SystemExit

    def write_to_disk(pkld,og_arg=None,debug=False):
      pre_pkld, pkld_type, h_idx = pkld
      og_arg = f"{repr(og_arg)}\n"
      pkld_obj = f"{repr(pre_pkld)}\n"
      pkld_hex = f"{pickle.dumps(tuple((h_idx,pkld_type,pre_pkld))).hex()}\n"
      if debug:
        pkld_strori = Path(self.pickle_path).parent.joinpath('eventpickle_ori')
        with open(pkld_strori,'a') as f:
          f.write(og_arg)
        pkld_strarg = Path(self.pickle_path).parent.joinpath('eventpickle_arg')
        with open(pkld_strarg,'a') as f:
          f.write(pkld_obj)
      pkld_strhex = Path(self.pickle_path).parent.joinpath('eventpickle_hex')
      with open(pkld_strhex,'a') as f:
        f.write(pkld_hex)
      return pkld_strhex

    main(arg)

    print('user_return')
    print(self.state.format_return)
    # frame.f_locals['__return__'] = return_value

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
