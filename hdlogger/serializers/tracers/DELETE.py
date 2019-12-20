from prettyprinter import pformat
import inspect
from functools import cached_property
class PickleableState:
  def __init__(self, kwds):
    self.attrs = list(kwds.keys())
    self.filename: str = kwds['format_filename']
    self.frame: PickleableFrame = kwds['frame']
    self.event: str = kwds['event']
    self.arg: Any = kwds['arg']
    self.f_locals: Dict = kwds['f_locals']
    self.count: int = kwds['count']
    self.function: str = kwds['function']
    self.module: str = kwds['module']
    self.lineno: int = kwds['lineno']
    self.stdlib: bool = kwds['stdlib']
    self.source: str = kwds['source']

  def __str__(self):
    l = []
    for attr in self.attrs:
      l.append(f"{attr}={getattr(self,attr,'None')}")
    s = "\n".join(l)
    return s

  def asdict(self):
    return self.__dict__

  @property
  def indent(self):
    idt = '\u0020' + (len(PickleableState.stack)-1)
    return idt

  stack = []
  @cached_property
  def format_call(self):
    symbol = "=>"
    PickleableState.stack.append(f"{self.module}.{self.function}")
    self.formatter1 = ( # default formatter
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
      f"{self.indent}|{symbol}|{self.function}|{self.locals}"
    )
    self.formatter2 = ( # indented formatter
      f"{self.indent}|{symbol}|{self.function}|{self.locals}|"
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
    )
    return self.formatter2

  @cached_property
  def format_line(self):
    symbol = "  "
    self.formatter1 = ( # default formatter
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
      f"{self.indent} |{symbol}|{self.source}|"
    )
    self.formatter2 = ( # indented formatter
      f"{self.indent} |{symbol}|{self.source}|"
      f"{self.count:>5}|{self.filename}:{self.lineno:<5}|{self.event:9}|"
    )
    return self.formatter2

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
    if PickleableState.stack and PickleableState.stack[-1] == f"{self.module}.{self.function}":
      PickleableState.stack.pop()
    return self.formatter2

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
    return self.formatter2

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

def make_pickleable_state(self) -> PickleableState:
  kwds = {
      "frame": pickleable_dispatch(self.frame),
      "event": self.event,
      "arg": pickleable_dispatch(self.arg),
      "f_locals": pickleable_dispatch(self.frame.f_locals),
      "count": self.count,
      "function": self.function,
      "module": self.module,
      "format_filename": self.format_filename,
      "lineno": self.lineno,
      "stdlib": self.stdlib,
      "source": self.source,
    }
  try:
    pickleable_state = PickleableState(**kwds)
  except:
    wf(stackprinter.format(sys.exc_info()),'logs/get_pickleable_state.log','a')
    raise SystemExit
  return pickleable_state


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


f = inspect.currentframe()
pf = make_pickleable_frame(f)
kwds = dict(
    frame=pf,
    event='call',
    arg=None,
    f_locals={'a':12},
    count=43,
    function="wefa",
    module="mod",
    format_filename="wetwfge",
    lineno=43,
    stdlib=False,
    source='f = inspect.currentframe()\n',
)
pst = PickleableState(kwds)
print(pst)



