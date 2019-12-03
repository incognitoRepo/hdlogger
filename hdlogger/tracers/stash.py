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
