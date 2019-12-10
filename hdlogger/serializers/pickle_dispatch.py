from typing import Iterable, Mapping, Sequence
from types import FrameType
from hdlogger.utils import *
import stackprinter, sys
import dill as pickle

def pickleable_dispatch(obj):
  try:
    return pickle.loads(pickle.dumps(obj))
  except:
    if isinstance(obj, bytes): obj = str(obj)
    if isinstance(obj,Iterable) and not isinstance(obj,str):
      if isinstance(obj, Mapping):
        return pickleable_dict(obj)
      elif isinstance(obj, Sequence):
        return pickleable_list(obj)
      else:
        wf(stackprinter.format(sys.exc_info()),'logs/models.pickleable_dispatch.log','a')
        raise
    elif isinstance(obj,FrameType):
      return pickleable_frame(obj)
    else:
      return pickleable_simple(obj)
    s = stackprinter.format(sys.exc_info())
    print(s)
    raise SystemExit(f"failure in pickleable_dispatch: cannot pickle {obj}")

def pickleable_environ(env):
  envd = dict(env)
  try:
    return pickleable_dict(envd)
  except:
    wf( stackprinter.format(sys.exc_info()),'logs/pickleable_env.tracer.log', 'a')
    raise

def pickleable_frame(frm):
  try:
    return pickle.loads(pickle.dumps(frm))
  except:
    wf('logs/pickleable_frame.tracer.log', stackprinter.format(sys.exc_info()))
    raise

def pickleable_dict(d):
  funclist = [
    lambda v: pickle.loads(pickle.dumps(v)),
    lambda v: jsonpickle.encode(v),
    lambda v: getattr(v,'__class__.__name__')
  ]
  d2 = {}
  for k,v in d.items():
    try:
      checked = checkfuncs(funclist,v)
      pickleable = next(filter(None,checked))
      d2[k] = pickleable
    except:
      s = stackprinter.format(sys.exc_info())
      wf( s,'logs/pickleable_dict.tracers.log',mode="a")
      wf((
        f"unable to pickle {d} due to:\n{k=}\n{v=}"
        f"{isinstance(v,GeneratorType)=}\n{pickle.loads(pickle.dumps(v))}"
      ),"a")
      raise SystemExit(
        f"unable to pickle {d} due to:\n{k=}\n{v=}"
        f"{isinstance(v,GeneratorType)=}\n{pickle.loads(pickle.dumps(v))}"
      )
  return d2

def pickleable_globals(g):
  cp = g.copy()
  cp['__builtins__'] = "-removed-"
  g2 = pickleable_dict(cp)
  return g2

def pickleable_list(l):
  if l == "": return ""
  try:
    ddl = pickle.dumps(l)
    assert pickle.loads(ddl)
    return l
  except:
      l2 = []
      for elm in l:
        try:
          dde = pickle.dumps(elm)
          assert pickle.loads(dde), f"cant load pickle.dumps(dde)={dde}"
          l2.append(dde)
        except:
          for test in [
            lambda: pickle.dumps(jsonpickle.encode(elm)),
            lambda: pickle.dumps(repr(elm)),
            lambda: pickle.dumps(str(elm)),
            lambda: pickle.dumps(elm.__class__.__name__)
            ]:
            try:
              dde = test()
              assert pickle.loads(dde), f"cant load pickle.dumps(dde)={dde}"
              l2.append(dde)
            except: pass
          wf( stackprinter.format(sys.exc_info()),'logs/models.unpickleable.log', 'a')
          raise SystemExit
      return l2

def pickleable_simple(s):
  if s == "": return ""
  try:
    dds = pickle.dumps(s)
    assert pickle.loads(dds)
    return s
  except:
    for test in [
      lambda: pickle.dumps(jsonpickle.encode(s)),
      lambda: pickle.dumps(repr(s)),
      lambda: pickle.dumps(str(s)),
      lambda: pickle.dumps(s.__class__.__name__)
      ]:
      try:
        dds = test()
        assert pickle.loads(dds), f"cant load pickle.dumps(dds)={dds}"
        return dds
      except:
        pass
    wf( stackprinter.format(sys.exc_info()),'logs/models.unpickleable.log', 'a')
    raise SystemExit



# DELETE TODO
for k,v in ps.__dict__.items():
  print(k)
  try: print(v)
  except: print('!err', v.keys())
  finally: print('--'*40)

