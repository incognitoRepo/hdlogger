import sys, os, collections, linecache, prettyprinter, stackprinter, inspect
from functools import singledispatchmethod, cached_property
from toolz.functoolz import compose_left
from itertools import count
from typing import Union, TypeVar
from types import CodeType
from hunter.const import SYS_PREFIX_PATHS
from hdlogger.utils import *
COL=80

class BaseEvt:
  def indent(self,char='\u0020',length=0):
    if length: return char * length
    else: return char * ((len(self.stack)-1))

  def static(self,static_vars):
    count,filename,lineno,event = static_vars
    s = f"i:{count:<4} ☰:{len(self.stack):<3}, {event[0]}{filename}.{lineno:<4}"
    return s

  def pseudo_static(self,symbol):
    s = f"{self.indent()}{symbol}"
    return s

  @property
  def nonstatic(self):
    function, f_locals = self.function, self.f_locals
    fmtdlns = prettyprinter.pformat(f_locals).splitlines()
    _first,*_rest = fmtdlns
    joinstr = '\n' + self.indent(length=len(function))
    rv = f"{function}{_first}\n{joinstr.join(_rest)}\n"
    return rv

  nonstatic_first = True
  def nonstatic_rightpad(self,static_vars,depth=None):
    wf(f"{static_vars=}\n",'logs/nonstatic_rpad.first.log','a')
    def _special_cases(lines): # Union[False,Any]
      """hardcoded logic for unique cases
      case1: len(lines) == 0
      case2: len(lines) == 1
      case3: len(lines) >= 2
      """
      wf(f"{lines=}\n",'logs/_special_cases.log','a')
      if len(lines) == 0:
        return self.nonstatic
      if len(lines) == 1:
        line0 = lines[0]
        s = (
          f"{idt}{self.symbol}"
          f"{line0:<{80-len(idt)}.{80-len(idt)}}|"
          f"├{self.static(static_vars)}┤"
        )
        return s
      if len(lines) >= 2:
        return False
      s = stackprinter.format()
      wf(s, f"logs/nonstatic_rpad.error.log",'a')
      return SystemExit(f"error in nonstatic_rpad: fucked logic")

    def firstline(fl):
      s = (
        f"{idt}{self.symbol}"
        f"{fl:<{80-len(idt)}.{80-len(idt)}}|"
        f"├{self.static(static_vars)}┤"
      )
      return s

    def formatlines(rls):
      l = [
        (f"{self.indent()} ."
        f"|{elm:<{ 80-(len(self.indent())) }}|"
        f"├{self.static(static_vars)}┤")
        for elm in rls]
      return '\n'.join(l)

    idt = self.indent()
    lines = self.nonstatic.strip().splitlines()
    if len(lines) == 0: return self.nonstatic
    if len(lines) == 1: return firstline(lines[0])
    if len(lines) >= 2:
      first = firstline(lines[0])
      rest = formatlines(lines[1:])
      fmtdlines = f"{first}\n{rest}\n"
      return fmtdlines
    s = stackprinter.format(sys.exc_info())
    wf(s, f"logs/nonstatic_rightpad.log",'a')
    raise SystemExit(f"nonstatic_rightpad.{__name__}")

class CallEvt(BaseEvt):
  symbol = "=>"
  def __init__(self, function=None, f_locals=None, callargs=None, varnames=None, stack=None):
    assert isinstance(f_locals,dict)
    self.function = function
    self.f_locals = f_locals
    self.callargs = callargs
    self.varnames = varnames
    self.stack = stack
    self.pid = id(self)

  def __str__(self):
    function, f_locals, pid = self.function, self.f_locals, self.pid
    assert isinstance(f_locals,dict)
    s = f"<CallEvt object: function={function}, f_locals={f_locals}, id={pid}>"
    return s

  def __iter__(self):
    return ((k,v) for k,v in self.__dict__.items())

  @property
  def pseudo_static(self):
    symbol = "=>"
    pseudo = super().pseudo_static(symbol)
    return pseudo

  @property
  def nonstatic(self):
    function, callargs = self.function, self.callargs
    fmtdlns = prettyprinter.pformat(self.callargs).splitlines()
    _first_as_str,*_rest_as_list = fmtdlns
    joinstr = '\n' + self.indent(length=len(function))
    rv = f"{function}{_first_as_str}\n{joinstr.join(_rest_as_list)}\n"
    return rv

  def pformat(self,count,filename,lineno,event):
    static_vars = (count,filename,lineno,event)
    s = f"{self.static(static_vars)}{self.pseudo_static}{self.nonstatic}"
    s2 = f"{self.pseudo_static}{self.nonstatic}"
    return s2

class LineEvt(BaseEvt):
  symbol = " _"
  def __init__(self, source=None, stack=None):
    self.source = source
    self.stack = stack
    self.pid = id(self)

  def __str__(self):
    source, pid = self.source, self.pid
    s = f"<LineEvt object: source={source}, id={pid}>"
    return s

  def __iter__(self):
    return ((k,v) for k,v in self.__dict__.items())

  def indent(self,char='\u0020'):
    idt = char * (len(self.stack)+1)
    return idt

  @property
  def pseudo_static(self):
    symbol = " _"
    pseudo = super().pseudo_static(symbol)
    return pseudo

  @property
  def nonstatic(self):
    source = self.source
    return source

  def pformat(self,count,filename,lineno,event):
    static_vars = (count,filename,lineno,event)
    s = f"{self.static(static_vars)}{self.pseudo_static}{self.nonstatic}"
    s2 = f"{self.pseudo_static}{self.nonstatic}"
    return s2

class RetnEvt(BaseEvt):
  symbol = "<="
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
    pseudo = super().pseudo_static(symbol)
    return pseudo

  @property
  def nonstatic(self):
    function, arg = self.function, self.arg
    fmtdlns = prettyprinter.pformat(arg).splitlines()
    _first,*_rest = fmtdlns
    joinstr = '\n' + self.indent(length=len(function))
    rv = f"{function}{_first}\n{joinstr.join(_rest)}\n"
    return rv

  def pformat(self,count,filename,lineno,event):
    static_vars = (count,filename,lineno,event)
    s = f"{self.static(static_vars)}{self.pseudo_static}{self.nonstatic}"
    s2 = f"{self.pseudo_static}{self.nonstatic}"
    return s2

class ExcpEvt(BaseEvt):
  symbol = " !"
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
    pseudo = super().pseudo_static(symbol)
    return pseudo

  @property
  def nonstatic(self):
    function, arg = self.function, self.arg
    fmtdlns = prettyprinter.pformat(arg).splitlines()
    _first,*_rest = fmtdlns
    joinstr = '\n' + self.indent(length=len(function))
    rv = f"{function}{_first}\n{joinstr.join(_rest)}\n"
    return rv

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
  _counter = count(0)

  def __init__(self, frame, event, arg):
    # wf(repr(arg)+"\n",'logs/01.initial_arg.state.log', 'a') # TODO: must uncomment
    self.frame = frame
    self.event = event
    self.arg = arg
    self.callargs = {a:inspect.getargvalues(frame).locals[a] for a in inspect.getargvalues(frame).args}
    self.st_count = next(State._counter)
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
    self.st_count = kwds['count']
    self.f_code = kwds['f_code']

  def __str__(self,color=False):
    return prettyprinter.pformat(self.__dict__)

class PickleableState:
  def __init__(self, kwds):
    self.attrs = list(kwds.keys())
    self.frame: PickleableFrame = kwds['frame']
    self.event: str = kwds['event']
    self.arg: Any = kwds['arg']
    self.callargs: List = kwds['callargs']
    self.f_locals: Dict = kwds['f_locals']
    self.f_code = self.frame.f_code
    self.st_count: int = kwds['st_count']
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
    PickleableState._stack.append(f"{self.module}.{self.function}")
    self.stack = PickleableState._stack[:]
    callevt = CallEvt(
      self.function,
      self.f_locals,
      self.callargs,
      self.f_code.co_varnames[:self.f_code.co_argcount],
      self.stack
    )
    static_vars = (self.st_count,self.filename,f"{self.lineno:<5}",self.event)
    static,pseudo,nonsta = callevt.static(static_vars),callevt.pseudo_static,callevt.nonstatic
    return static+pseudo+nonsta

  def pkl_format_call(self):
    PickleableState._stack.append(f"{self.module}.{self.function}")
    self.stack = PickleableState._stack[:]
    callevt = CallEvt(
      self.function,
      self.f_locals,
      self.callargs,
      self.f_code.co_varnames[:self.f_code.co_argcount],
      self.stack
    )
    static_vars = (self.st_count,self.filename,f"{self.lineno:<5}",self.event)
    static,pseudo,nonsta = callevt.static(static_vars),callevt.pseudo_static,callevt.nonstatic
    return (static, pseudo, nonsta)

  @property
  def format_line(self):
    lineevt = LineEvt(self.source, self.stack)
    static_vars = (self.st_count,self.filename,f"{self.lineno:<5}",self.event)
    static,pseudo,nonsta = lineevt.static(static_vars),lineevt.pseudo_static,lineevt.nonstatic
    self.stack = PickleableState._stack[:]
    return static+pseudo+nonsta

  def pkl_format_line(self):
    lineevt = LineEvt(self.source, self.stack)
    static_vars = (self.st_count,self.filename,f"{self.lineno:<5}",self.event)
    static,pseudo,nonsta = lineevt.static(static_vars),lineevt.pseudo_static,lineevt.nonstatic
    self.stack = PickleableState._stack[:]
    return (static, pseudo, nonsta)

  @property
  def format_return(self):
    retnevt = RetnEvt(self.function, self.arg, self.stack)
    static_vars = (self.st_count,self.filename,f"{self.lineno:<5}",self.event)
    static,pseudo,nonsta = retnevt.static(static_vars),retnevt.pseudo_static,retnevt.nonstatic
    # if PickleableState._stack and PickleableState._stack[-1] == f"{self.module}.{self.function}":
      # PickleableState._stack.pop()
    if PickleableState._stack:
      PickleableState._stack.pop()
    self.stack = PickleableState._stack[:]
    return static+pseudo+nonsta

  def pkl_format_return(self):
    retnevt = RetnEvt(self.function, self.arg, self.stack)
    static_vars = (self.st_count,self.filename,f"{self.lineno:<5}",self.event)
    static,pseudo,nonsta = retnevt.static(static_vars),retnevt.pseudo_static,retnevt.nonstatic
    if PickleableState._stack:
      PickleableState._stack.pop()
    self.stack = PickleableState._stack[:]
    return (static, pseudo, nonsta)

  @property
  def format_exception(self):
    excpevt = ExcpEvt(self.function, self.arg, self.stack)
    static_vars = (self.st_count,self.filename,f"{self.lineno:<5}",self.event)
    static,pseudo,nonsta = excpevt.static(static_vars),excpevt.pseudo_static,excpevt.nonstatic
    self.stack = PickleableState._stack[:]
    return static+pseudo+nonsta

  def pkl_format_exception(self):
    excpevt = ExcpEvt(self.function, self.arg, self.stack)
    static_vars = (self.st_count,self.filename,f"{self.lineno:<5}",self.event)
    static,pseudo,nonsta = excpevt.static(static_vars),excpevt.pseudo_static,excpevt.nonstatic
    self.stack = PickleableState._stack[:]
    return (static, pseudo, nonsta)

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


