from pydantic import BaseModel, ValidationError
from typing import Type
from types import TracebackType


class TraceHookCallbackException(BaseModel):
  """self._arg = (<class 'KeyError'>, KeyError(b'LANGUAGE'), <traceback object at 0x11317f380>, )"""
  klass: Type[BaseException]
  instance: BaseException
  traceback: TracebackType

try: 1/0
except: exc = sys.exc_info()

TraceHookCallbackException(*exc)
