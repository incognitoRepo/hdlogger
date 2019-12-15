import sys, os, collections, linecache, prettyprinter
from functools import singledispatchmethod, cached_property
from toolz.functoolz import compose_left
from itertools import count
from typing import Union, TypeVar
from hunter.const import SYS_PREFIX_PATHS
from hdlogger.utils import *

class BaseEvt:
  @property
  def indent(self):
    idt = '\u0020' * (len(self.stack)-1)
    idt = '-' * (len(self.stack)-1)
    return idt

  def static(self,static_vars):
    count,filename,lineno,event = static_vars
    s = f"i:{count:<4} ☰:{len(self.stack)}, {event}{filename}.{lineno:<4}"
    return s

  def nonstatic_rightpad(self,static_vars):
    nonstls = self.nonstatic.splitlines()
    _indented = [self.indent+elm for elm in nonstls]
    _sectioned = [f"{elm:<80}" for elm in _indented]
    _static = self.static(static_vars)
    _metad = [f"├{self.pseudo_static}┤|{elm}|├{_static}┤" for elm in _sectioned]
    s = 'n'.join(_metad)
    return s


class CallEvt(BaseEvt):
  def __init__(self, function=None, f_locals=None, stack=None):
    self.function = function
    self.f_locals = f_locals
    self.stack = stack
    self.pid = id(self)

  def __str__(self):
    function, f_locals, pid = self.function, self.f_locals, self.pid
    s = f"<CallEvt object: function={function}, f_locals={f_locals}, id={pid}>"
    return s

  def __iter__(self):
    return ((k,v) for k,v in self.__dict__.items())

  @property
  def pseudo_static(self):
    symbol = "=>"
    pseudo = f"{self.indent}{symbol}|"
    return pseudo

  @property
  def nonstatic(self):
    function, f_locals = self.function, self.f_locals
    def recursive(l,first=True):
      if not l: return ""
      elm = l[0]
      if first:
        first = False
        return f"{function}{elm}\n" + recursive(l[1:],first)
      else:
        return f"{len(function)*' '}{elm}\n" + recursive(l[1:],first)
    nonst = recursive(prettyprinter.pformat(f_locals).splitlines())
    return nonst

  def pformat(self,count,filename,lineno,event):
    static_vars = (count,filename,lineno,event)
    s = f"{self.static(static_vars)}{self.pseudo_static}{self.nonstatic}"
    s2 = f"{self.pseudo_static}{self.nonstatic}"
    return s2

class LineEvt(BaseEvt):
  def __init__(self, source=None, stack=None):
    wf(source,'logs/LineEvt.source.log','a')
    self.source = source
    self.stack = stack
    self.pid = id(self)

  def __str__(self):
    source, pid = self.source, self.pid
    s = f"<LineEvt object: source={source}, id={pid}>"
    return s

  def __iter__(self):
    return ((k,v) for k,v in self.__dict__.items())

  @property
  def pseudo_static(self):
    symbol = " -"
    pseudo = f"{self.indent}{symbol}|"
    return pseudo

  @property
  def nonstatic(self):
    nonst = self.source
    return nonst

  def pformat(self,count,filename,lineno,event):
    static_vars = (count,filename,lineno,event)
    s = f"{self.pseudo_static}{self.nonstatic}{self.static(static_vars)}"
    s2 = f"{self.pseudo_static}{self.nonstatic}"
    return s2

class RetnEvt(BaseEvt):
  def __init__(self, function, arg, stack=None):
    self.function = function
    self.arg = arg
    self.stack = stack
    self.id = id(self)

  def __str__(self):
    function, arg, pid = self.function, self.arg, self.pid
    s = f"<RetnEvt object: function={function}, arg={arg}, id={pid}>"
    return s

  def __iter__(self):
    return ((k,v) for k,v in self.__dict__.items())

  @property
  def pseudo_static(self):
    symbol = "<="
    pseudo = f"{self.indent}{symbol}|"
    return pseudo

  @property
  def nonstatic(self):
    function, arg = self.function, self.arg
    def recursive(l,first=True):
      if not l: return ""
      elm = l[0]
      if first:
        first = False
        return f"{function}{elm}\n" + recursive(l[1:],first)
      else:
        return f"{len(function)*' '}{elm}\n" + recursive(l[1:],first)
    nonst = recursive(prettyprinter.pformat(arg).splitlines())
    return nonst

  def pformat(self,count,filename,lineno,event):
    static_vars = (count,filename,lineno,event)
    s = f"{self.static(static_vars)}{self.pseudo_static}{self.nonstatic}"
    s2 = f"{self.pseudo_static}{self.nonstatic}"
    return s2

class ExcpEvt(BaseEvt):
  def __init__(self, function, arg, stack=None):
    self.function = function
    self.arg = arg
    self.stack = stack
    self.id = id(self)

  def __str__(self):
    function, arg, pid = self.function, self.arg, self.pid
    s = f"<ExcpEvt object: function={function}, arg={arg}, id={pid}>"
    return s

  def __iter__(self):
    return ((k,v) for k,v in self.__dict__.items())

  @property
  def pseudo_static(self):
    symbol = " !"
    pseudo = f"{self.indent}{symbol}|"
    return pseudo

  @property
  def nonstatic(self):
    function, arg = self.function, self.arg
    def recursive(l,first=True):
      if not l: return ""
      elm = l[0]
      if first:
        first = False
        return f"{function}{elm}\n" + recursive(l[1:],first)
      else:
        return f"{len(function)*' '}{elm}\n" + recursive(l[1:],first)
    nonst = recursive(prettyprinter.pformat(arg).splitlines())
    return nonst

  def pformat(self,count,filename,lineno,event):
    static_vars = (count,filename,lineno,event)
    s = f"{self.static(static_vars)}{self.pseudo_static}{self.nonstatic}"
    s2 = f"{self.pseudo_static}{self.nonstatic}"
    return s2

class State:
  SYS_PREFIX_PATHS = set((
    sys.prefix,
    sys.exec_prefix,
    os.path.dirname(os.__file__),
    os.path.dirname(collections.__file__),))
  counter = count(0)

  def __init__(self, frame, event, arg):
    wf(repr(arg)+"\n",'logs/01.initial_arg.state.log', 'a')
    self.frame = frame
    self.event = event
    self.arg = arg
    self.count = next(State.counter)
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
    self.stack = None
    self._call = None
    self._line = None
    self._return = None
    self._exception = None
    self._serialized_arg = None
    self._serialized_locals = None

  @cached_property
  def format_filename(self):
    if not isinstance(self.filename,Path):
      filename = Path(self.filename)
    stem = f"{filename.stem:>10.10}"
    return stem

  _stack = []
  @property
  def format_call(self):
    raise NotImplementedError("Must implement PickleableState.format_call")

  @property
  def format_line(self):
    raise NotImplementedError("Must implement PickleableState.format_line")

  @property
  def format_return(self):
    raise NotImplementedError("Must implement PickleableState.format_return")

  @property
  def format_exception(self):
    raise NotImplementedError("Must implement PickleableState.format_exception")

class PickleableFrame:
  def __init__(self, kwds):
    self.filename = kwds['filename']
    self.lineno = kwds['lineno']
    self.function = kwds['function']
    self.local_vars = kwds['local_vars']
    self.code_context = kwds['code_context']
    self.count = kwds['count']

  def __str__(self,color=False):
    return prettyprinter.pformat(self.__dict__)

class PickleableState:
  def __init__(self, kwds):
    self.attrs = list(kwds.keys())
    self.frame: PickleableFrame = kwds['frame']
    self.event: str = kwds['event']
    self.arg: Any = kwds['arg']
    self.f_locals: Dict = kwds['f_locals']
    self.count: int = kwds['count']
    self.function: str = kwds['function']
    self.module: str = kwds['module']
    self.filename: str = kwds['format_filename']
    self.lineno: int = kwds['lineno']
    self.stdlib: bool = kwds['stdlib']
    self.source: str = kwds['source']
    self.stack: List[str] = kwds['stack']

  def __str__(self):
    l = []
    for attr in self.attrs:
      l.append(f"{attr}={getattr(self,attr,'None')}")
    s = "\n".join(l)
    return s

  def __iter__(self):
    return ((k,v) for k,v in self.asdict().items())

  def asdict(self):
    return self.__dict__

  @property
  def indent(self):
    idt = '\u0020' * (len(PickleableState._stack)-1)
    return idt

  _stack = []
  @property
  def format_call(self):
    callevt = CallEvt(self.function, self.f_locals, PickleableState._stack)
    PickleableState._stack.append(f"{self.module}.{self.function}")
    static_vars = (self.count,self.filename,f"{self.lineno:<5}",self.event)
    static,pseudo,nonsta = callevt.static(static_vars),callevt.pseudo_static,callevt.nonstatic
    self.stack = [elm for elm in PickleableState._stack]
    return static+pseudo+nonsta

  @property
  def format_line(self):
    lineevt = LineEvt(self.source, PickleableState._stack)
    static_vars = (self.count,self.filename,f"{self.lineno:<5}",self.event)
    static,pseudo,nonsta = lineevt.static(static_vars),lineevt.pseudo_static,lineevt.nonstatic
    self.stack = PickleableState._stack[:]
    return static+pseudo+nonsta

  @property
  def format_return(self):
    retnevt = RetnEvt(self.function, self.arg, PickleableState._stack)
    static_vars = (self.count,self.filename,f"{self.lineno:<5}",self.event)
    static,pseudo,nonsta = retnevt.static(static_vars),retnevt.pseudo_static,retnevt.nonstatic
    # if PickleableState._stack and PickleableState._stack[-1] == f"{self.module}.{self.function}":
      # PickleableState._stack.pop()
    wf(f"1. {str(PickleableState._stack)}\n",'logs/retnevt.popstate.log','a')
    if PickleableState._stack:
      PickleableState._stack.pop()
      wf(f"2. {str(PickleableState._stack)}\n",'logs/retnevt.popstate.log','a')
    self.stack = PickleableState._stack[:]
    wf(f"3. {str(self.stack)}\n",'logs/retnevt.popstate.log','a')
    return static+pseudo+nonsta

  @property
  def format_exception(self):
    excpevt = ExcpEvt(self.function, self.arg, PickleableState._stack)
    static_vars = (self.count,self.filename,f"{self.lineno:<5}",self.event)
    static,pseudo,nonsta = excpevt.static(static_vars),excpevt.pseudo_static,excpevt.nonstatic
    self.stack = PickleableState._stack[:]
    return static+pseudo+nonsta

class PickleableGenerator:
  def __init__(self,state,f_locals,pid):
    self.state = state
    self.locals = f_locals
    self.pid = pid

  def __str__(self):
    state, f_locals, pid = self.state, self.locals, self.pid
    s = f"<generator object: state={state}, locals={f_locals}, id={pid}>"
    return s

class PickleableEnviron:
  def __init__(self, kwds):
    d = {}
    for k,v in kwds.items():
      if ':' in v: v = prettyprinter.pformat(v.split(':'))
      # if k == "LS_COLORS": v = prettyprinter.pformat(v.split(':'))
      setattr(self, k, kwds[k])

  def __str__(self,color=False):
    return prettyprinter.pformat(self.__dict__)

class PickleableTraceback:
  def __init__(self,lasti,lineno):
    self.lasti = lasti
    self.lineno = lineno

class GenericPickleableMapping:
  pass

class PickleableOptparseOption:
  def __init__(self,module,classname):
    self.module = module
    self.classname = classname
    self.id = id(self)  #  0x%x:

  def __iter__(self):
    return ((k,v) for k,v in self.__dict__.items())

  def __str__(self):
    l = []
    for k,v in self.__dict__.items():
      l.append(f"{k}={v}")
    s = f"{self.module}.{self.classname}, {id=}"
    return s


