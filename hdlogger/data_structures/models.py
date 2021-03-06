from pydantic import BaseModel, PydanticValueError, ValidationError, validator, Field
from prettyprinter import pformat
import dill, stackprinter, sys, optparse
import dill as pickle
from typing import Type, Any, Optional, Dict, Mapping, Sequence, Iterable
from types import TracebackType, FrameType
import traceback, jsonpickle

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

class TraceHookCallbackCall(BaseModel):
  call_args: Any

class TraceHookCallbackLine(BaseModel):
  line_vars: Any

class TraceHookCallbackReturn(BaseModel):
  return_value: Any

  def __str__(self):
    return pformat(dict(self))

  def __getstate__(self):
    state = self.__dict__.copy()
    return state

  def __setstate__(self, state):
    self.__dict__.update(state)

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

def pickle_compat_enforcer(obj):
  """i only need to make 1 distinction: container?"""

class UnpickleableError(PydanticValueError):
  code = 'incorrigibly_unpickeable'
  msg_template = 'attempted `[pickle,jsonpickle,repr,str]` for "{type(v)=}"'

def pickleable_dict(d):
  with open('logs/models.pickleable_dict.log','a') as f:
    f.write(f"\n{type(d)=}\n{d.keys()=}\n")
    # for k in d:
    #   f.write(f"{d[k]=}\n")
  if d == "": return ""
  try:
    ddd = dill.dumps(d)
    assert str(dill.loads(ddd)), d
    return d
  except:
    d2 = {}
    for k in d:
      # with open('logs/models.pickleable_dict2.log','a') as f:
        # f.write(f"{k}={d}")
      try:
        ddv = dill.dumps(d[k])
        ddvstr = str(dill.loads(ddv))
        assert str(dill.loads(ddv)), f"cant load dill.dumps(ddv)={ddv}"
        d2[k] = ddv
      except:
        tests = [jsonpickle.encode,repr,str,lambda _,v: getattr(v,'__class__.__name__')]

        def check_pickleability(func,obj): return dill.pickles(func(obj))
        for test in tests:
          try:
            check_pickleability(test,d[k])
            d2.update({k:test(d[k])})
          except:
            raise

        # with open('logs/models.unpickleable3.log','a') as f:
        #   f.write("jsonpickle: "+dill.loads(dill.dumps(jsonpickle.encode(d[k])))+"\n\n")
        #   f.write("repr: "+dill.loads(dill.dumps(repr(d[k])))+"\n\n"
        #   f.write("str: "+dill.loads(dill.dumps(str(d[k])))+"\n\n"
        #   f.write("__class__.__name__: "+dill.loads(dill.dumps(d[k].__class__.__name__))+"\n\n"
        # for test in [
        #   lambda: "jsonpickle: "+dill.loads(dill.dumps(jsonpickle.encode(d[k])))+"\n\n",
        #   lambda: "repr: "+dill.loads(dill.dumps(repr(d[k])))+"\n\n",
        #   lambda: "str: "+dill.loads(dill.dumps(str(d[k])))+"\n\n",
        #   lambda: "__class__.__name__: "+dill.loads(dill.dumps(d[k].__class__.__name__))+"\n\n",
        #   ]:
        #   try:
        #     ddv = test()
        #     d2[k] = ddv
        #   except: pass
        with open('logs/models.unpickleable.log','a') as f:
          f.write(stackprinter.format(sys.exc_info()))
        raise SystemExit
    return d2

def pickleable_list(l):
  if l == "": return ""
  try:
    ddl = dill.dumps(l)
    assert dill.loads(ddl)
    return l
  except:
      l2 = []
      for elm in l:
        try:
          dde = dill.dumps(elm)
          assert dill.loads(dde), f"cant load dill.dumps(dde)={dde}"
          l2.append(dde)
        except:
          for test in [
            lambda: dill.dumps(jsonpickle.encode(elm)),
            lambda: dill.dumps(repr(elm)),
            lambda: dill.dumps(str(elm)),
            lambda: dill.dumps(elm.__class__.__name__)
            ]:
            try:
              dde = test()
              assert dill.loads(dde), f"cant load dill.dumps(dde)={dde}"
              l2.append(dde)
            except: pass
          with open('logs/models.unpickleable.log','a') as f:
            f.write(stackprinter.format(sys.exc_info()))
          raise SystemExit
      return l2

def pickleable_simple(s):
  if s == "": return ""
  try:
    dds = dill.dumps(s)
    assert dill.loads(dds)
    return s
  except:
    for test in [
      lambda: dill.dumps(jsonpickle.encode(s)),
      lambda: dill.dumps(repr(s)),
      lambda: dill.dumps(str(s)),
      lambda: dill.dumps(s.__class__.__name__)
      ]:
      try:
        dds = test()
        assert dill.loads(dds), f"cant load dill.dumps(dds)={dds}"
        return dds
      except:
        pass
    with open('logs/models.unpickleable.log','a') as f:
      f.write(stackprinter.format(sys.exc_info()))
    raise SystemExit


class PickleableDict(BaseModel):
  d: Optional[Dict[str, Any]] = None

  @validator('d',pre=True)
  def make_pickleable(cls, v):
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
      raise

  @validator('d',each_item=True)
  def check_pickleable(cls, v):
    assert dill.pickles(v), f'{v} cannot be pickled (dilled)'
    return v

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
    if self.d is None: return "None"
    return pformat(dict(self))

  def __getstate__(self):
    state = self.__dict__.copy()
    return state

  def __setstate__(self, state):
    self.__dict__.update(state)

