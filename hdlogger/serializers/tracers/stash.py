# vscode-fold=1

class HiDefTracer:
  def user_return_no_generator(self, frame, return_value):
    print('user_return_no_generator')
    print("__return__1" + getattr(frame.f_locals,'__return__','dne'))
    print(self.state.format_return)
    frame.f_locals['__return__'] = return_value
    print("__return__2" + getattr(frame.f_locals,'__return__','dne'))

  def user_return_f_locals(self, frame, return_value):
    print('user_return_f_locals')
    arg = frame.f_locals['rv']
    print("arg:\n" + "\n".join([repr(elm) for elm in arg]))
    print("__return__1" + getattr(frame.f_locals,'__return__','dne'))
    print(self.state.format_return)
    frame.f_locals['__return__'] = return_value
    frame.f_locals['rv'] = [123]
    print("__return__2" + getattr(frame.f_locals,'__return__','dne'))

  def user_return_w_inspect(self, frame, return_value):
    print('user_return_w_inspect')
    arg = frame.f_locals['rv']
    print(f"{inspect.getgeneratorstate(return_value)}")
    print(f"{inspect.getgeneratorlocals(return_value)}")
    print("__return__1" + getattr(frame.f_locals,'__return__','dne'))
    print(self.state.format_return)
    frame.f_locals['__return__'] = return_value
    frame.f_locals['rv'] = [123]
    print("__return__2" + getattr(frame.f_locals,'__return__','dne'))

  def user_return_w_jsonpickle(self, frame, return_value):
    # TODO
    pass

  def user_return_w_itertools_tee(self, frame, return_value):
    # TODO
    pass

class PickleableFunction:
  def __init__(self, lineno):
    self.lineno = lineno

def pickle_function(function):
  kwds = {'lineno':function.f_lineno}
  return unpickle_function, (kwds,)

def unpickle_function(kwds):
  return PickleableFunction(**kwds)

def trest():
  df = pd.DataFrame(columns=["a","bee","c"])
  d = {"a":325,"bee":['d','r'],"c": 3}
  l = [d]
  df.append(l)
  df2 = df.append(l)
  df3 = df2.append(l)
  l2 = []
  d2 = {"bee":['rt'],"c":435,"a":4}
  df3.append(l2.append(d2))
