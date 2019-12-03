from pydantic import BaseModel, PydanticValueError, ValidationError, validator, Field
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
  tb: Optional[PydanticTraceback] = None # traceback

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

def pickle_compat_enforcer(obj):
  """i only need to make 1 distinction: container?"""

class UnpickleableError(PydanticValueError):
  code = 'incorrigibly_unpickeable'
  msg_template = 'attempted `[pickle,jsonpickle,repr,str]` for "{type(v)=}"'

class PickleableDict(BaseModel):
  pick_dict: Optional[Dict[str, Any]] = Field(default=None)

  @validator('pick_dict')
  def must_be_pickleable(cls, v):
    try:
      return dill.loads(dill.dumps(v))
    except:
      try:
        potentially_pickleable = PickleableDict.make_pickleable(v)
        return dill.loads(dill.dumps(potentially_pickleable))
      except:
        with open('logs/models.pickleabledict.log','w') as f:
          f.write(stackprinter.format(sys.exc_info()))
        raise UnpickleableError(v)

  @classmethod
  def make_pickleable(dct):
    d = {}
    for k,v in dct.items():
      try:
        dd = dill.dumps(v)
        assert dill.loads(dd), f"cant load dill.dumps(v)={dd}"
        d[k] = dd
      except:
        for test in [
          lambda: dill.dumps(jsonpickle.encode(v)),
          lambda: dill.dumps(repr(v)),
          lambda: dill.dumps(str(v)),
          lambda: dill.dumps(v.__class__.__name__)
          ]:
          try:
            dd = test()
            assert dill.loads(dd), f"cant load dill.dumps(v)={dd}"
            d[k] = dd
          except: pass
        with open('logs/models.unpickleable.log','a') as f:
          f.write(stackprinter.format(sys.exc_info()))
        raise SystemExit
    return d

  def __str__(self):
    if self.pick_dict is None: return "None"
    return pformat(dict(self))

  def __getstate__(self):
    state = self.__dict__.copy()
    return state

  def __setstate__(self, state):
    self.__dict__.update(state)
