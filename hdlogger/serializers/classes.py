import sys, os, collections, linecache
from functools import singledispatchmethod, cached_property
from itertools import count
from typing import Union, TypeVar
from hunter.const import SYS_PREFIX_PATHS
from hdlogger.utils import *

class CallEvt:
  def __init__(self, function=None, f_locals=None):
    self.function = function
    self.f_locals = f_locals
    self.pid = id(self)

  def __iter__(self):
    return ((k,v) for k,v in self.__dict__.items())

  def __str__(self):
    function, f_locals, pid = self.function, self.f_locals, self.pid
    s = f"<CallEvt object: function={function}, f_locals={f_locals}, id={pid}>"
    return s

class LineEvt:
  def __init__(self, source=None):
    self.source = source
    self.pid = id(self)

  def __iter__(self):
    return ((k,v) for k,v in self.__dict__.items())

  def __str__(self):
    source, pid = self.source, self.pid
    s = f"<LineEvt object: source={source}, id={pid}>"
    return s

class RetnEvt:
  def __init__(self, function, arg):
    self.function = function
    self.arg = arg
    self.id = id(self)

  def __iter__(self):
    return ((k,v) for k,v in self.__dict__.items())

  def __str__(self):
    function, arg, pid = self.function, self.arg, self.pid
    s = f"<RetnEvt object: function={function}, arg={arg}, id={pid}>"
    return s

class ExcpEvt:
  def __init__(self, function, arg):
    self.function = function
    self.arg = arg
    self.id = id(self)

  def __iter__(self):
    return ((k,v) for k,v in self.__dict__.items())

  def __str__(self):
    function, arg, pid = self.function, self.arg, self.pid
    s = f"<ExcpEvt object: function={function}, arg={arg}, id={pid}>"
    return s


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

  stack = []
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
    return pformat(self.__dict__)

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

  def __str__(self):
    l = []
    for attr in self.attrs:
      l.append(f"{attr}={getattr(self,attr,'None')}")
    s = "\n".join(l)
    return s

  def __iter__(self):
    yield from self.asdict().items()

  def asdict(self):
    return self.__dict__

  @property
  def indent(self):
    idt = '\u0020' * (len(PickleableState.stack)-1)
    return idt

  def static_str(self):
    static = f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
    return static

  def pseudo_static_str(self,symbol):
    pseudo = f"{self.indent}|{symbol}"
    return pseudo_static

  @singledispatchmethod
  def non_static_str(self, arg):
    raise NotImplementedError("you must implement the non_static_str method")

  @non_static_str.register
  def _(self, arg:type("CallEvt",(),{})):
    function, f_locals = arg
    nonst = f"{function}|{f_locals}|"
    return nonst

  @non_static_str.register
  def _(self, arg:LineEvt):
    source = arg
    nonst = f"{source}|"
    return nonst

  @non_static_str.register
  def _(self, arg:RetnEvt):
    function, arg = arg
    nonst = f"{function}|{arg}|"
    return nonst

  @non_static_str.register
  def _(self, arg:ExcpEvt):
    function, arg = arg
    nonst = f"{function}|{arg}|"
    return nonst

  stack = []
  @cached_property
  def format_call(self):
    symbol = "=>"
    callevt = CallEvt()
    d = {'function':self.function, 'f_locals':f_locals}
    callevt = type('CallEvt', (), d)
    PickleableState.stack.append(f"{self.module}.{self.function}")
    self.formatter1 = ( # default formatter
      f"{self.static_str}"
      f"{self.pseudo_static_str(symbol)}"
      f"{self.non_static_str(type('CallEvt',(),{'function':self.function,'f_locals':f_locals}))}"
    )
    self.formatter2 = ( # indented formatter
      f"{self.pseudo_static_str(symbol)}"
      f"{self.non_static_str(type('CallEvt',(),{'function':self.function,'f_locals':f_locals}))}"
      f"{self.static_str}"
    )
    self.formatter3 = ( # just sauce
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
      f"{self.indent}|{symbol}|{self.function}|{self.f_locals}|"
    )
    return self.formatter3

  @cached_property
  def format_line(self):
    symbol = "  "
    self.formatter1 = ( # default formatter
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
      f"{self.indent} |{symbol}|{self.source.rstrip()}|"
    )
    self.formatter2 = ( # indented formatter
      f"{self.indent} |{symbol}|{self.source.rstrip()}|"
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
    )
    self.formatter3 = ( # just sauce
      f"{self.indent} |{symbol}|{self.source.rstrip()}|"
    )
    return self.formatter3

  @cached_property
  def format_return(self):
    symbol = "<="
    self.formatter1 = ( # default formatter
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
      f"{self.indent}|{symbol}|{self.function}|{self.arg}"
    )
    self.formatter2 = ( # indented formatter
      f"{self.indent}|{symbol}|{self.function}|{self.arg}|"
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
    )
    self.formatter3 = ( # just savce
      f"{self.indent}|{symbol}|{self.function}|{self.arg}|"
    )
    if PickleableState.stack and PickleableState.stack[-1] == f"{self.module}.{self.function}":
      PickleableState.stack.pop()
    return self.formatter3

  @cached_property
  def format_exception(self):
    symbol = " !"
    self.formatter1 = ( # default formatter
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
      f"{self.indent}|{symbol}|{self.function}|{self.arg}"
    )
    self.formatter2 = ( # indented formatter
      f"{self.indent}|{symbol}|{self.function}|{self.arg}|"
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
    )
    self.formatter3 = ( # just savce
      f"{self.indent}|{symbol}|{self.function}|{self.arg}|"
    )
    return self.formatter3

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
      setattr(self, k, kwds[k])

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

  def __str__(self):
    l = []
    for k,v in self.__dict__.items():
      l.append(f"{k}={v}")
    s = f"{self.module}.{self.classname}, {id=}"
    return s
