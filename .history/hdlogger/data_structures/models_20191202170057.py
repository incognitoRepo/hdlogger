from pydantic import BaseModel, ValidationError
from prettyprinter import pformat
import dill
from typing import Type, Any, Optional, Dict
from types import TracebackType
import traceback

"""self._arg = (<class 'KeyError'>, KeyError(b'LANGUAGE'), <traceback object at 0x11317f380>, )"""

class PydanticBaseException(BaseException):
  @classmethod
  def __get_validators__(cls):
    yield cls.validate

  @classmethod
  def validate(cls, v):
    if not isinstance(v, BaseException):
      raise ValueError(f'pydantic base exception: BaseException expected not {type(v)=}')
    return v

class PydanticTraceback(BaseException):
  """demo:
    try: 1/0
    except: exc = sys.exc_info()
    d = dict(zip(['etype','value','traceback'],exc))
    try:
      TraceHookCallbackException(**d)
    except ValidationError as e:
      print(e.json())
  """
  @classmethod
  def __get_validators__(cls):
    yield cls.validate

  @classmethod
  def validate(cls, v):
    if not isinstance(v, TracebackType):
      raise ValueError(f'pydantic base exception: BaseException expected not {type(v)=}')
    return v

class TraceHookCallbackException(BaseModel):
  etype: Type[BaseException] # class
  value: PydanticBaseException # instance
  tb: Optional[PydanticTraceback]=None # traceback

  def __str__(self):
    return pformat(dict(self))

  def __getstate__(self):
    state = self.__dict__.copy()
    state['tb'] = traceback.format_tb(self.tb)
    return state

  def __setstate__(self, state):
    self.__dict__.update(state)

class TraceHookCallbackReturn(BaseModel):
  return_value: Any

  def __str__(self):
    return pformat(dict(self))

  def __getstate__(self):
    state = self.__dict__.copy()
    return state

  def __setstate__(self, state):
    self.__dict__.update(state)

class PickleableDict(BaseModel):
  d = Dict

  def make_pickleable(dct):
    for k,v in dct.items():
      try:
        dd = dill.dumps(v)
        assert dill.loads(dd), f"cant load dill.dumps(v)={dd}"
      except:
        with open('logs/models.unpickleable.log','a') as f:
          f.write(
            f"{k=}\n{repr(v)=}\n{str(v)=}\n"
          )
