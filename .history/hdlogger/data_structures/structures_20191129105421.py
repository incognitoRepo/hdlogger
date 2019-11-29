from pydantic import BaseModel, ValidationError
from typing import Type
from types import TracebackType

"""self._arg = (<class 'KeyError'>, KeyError(b'LANGUAGE'), <traceback object at 0x11317f380>, )"""

class PydanticBaseException(BaseException):
  @classmethod
  def __get_validators__(cls):
    yield cls.validate

  @classmethod
  def validate(cls, v):
    if not issubclass(v, BaseException):
      raise ValueError(f'pydantic base exception: BaseException expected not {type(v)=}')
    return v

class PydanticTraceback(BaseException):
  @classmethod
  def __get_validators__(cls):
    yield cls.validate

  @classmethod
  def validate(cls, v):
    if not isinstance(v, TracebackType):
      raise ValueError(f'pydantic base exception: BaseException expected not {type(v)=}')
    return v

class TraceHookCallbackException(BaseModel):
  klass: Type[BaseException]
  instance: PydanticBaseException
  traceback: PydanticTraceback

try: 1/0
except: exc = sys.exc_info()
d = dict(zip(['klass','instance','traceback'],e))
try:
  TraceHookCallbackException(d)
except ValidationError as e:
  print(e.json())

