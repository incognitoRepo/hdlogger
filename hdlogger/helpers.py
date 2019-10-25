def get_answer():
  """Get an answer."""
  return True

class MockFrame:
  def string(self):
    example = "<frame at 0x108756e50, file '<ipython-input-1-24d5ecc75ccb>', line 1, code <module>>"
    print(f"{example=}")

  def attributes(self,verbose=False):
    attrsv = ['f_back','f_builtins',
      'f_code','f_globals','f_lasti',
      'f_lineno','f_locals','f_trace',
      'f_trace_lines','f_trace_opcodes']
    attrs = ['f_back','f_code','f_lasti',
      'f_lineno','f_trace','f_trace_lines',
      'f_trace_opcodes']
    attrsj = '\n'.join(attrs)
    print(attrsj)
    return attrs

  def get_attributes(self,f):
    if f:
      attrs = self.attributes(verbose=False)
      d = {k:getattr(f,k) for k in attrs}
      for k,v in d.items():
        print(f"{k}={v}")
    else:
      raise Exception

class MockCode:
  def string(self):
    example = '<code object <module> at 0x106c22240, file "<ipython-input-1-24d5ecc75ccb>", line 1>'
    print(f"{example=}")

  def attributes(self,verbose=False):
    attrsv = [
      'co_argcount',
      'co_cellvars',
      'co_code',
      'co_consts',
      'co_filename',
      'co_firstlineno',
      'co_flags',
      'co_freevars',
      'co_kwonlyargcount',
      'co_lnotab',
      'co_name',
      'co_names',
      'co_nlocals',
      'co_posonlyargcount',
      'co_stacksize',
      'co_varnames']
    attrs = [
      'co_argcount',
      'co_cellvars',
      'co_code',
      'co_consts',
      'co_filename',
      'co_firstlineno',
      'co_flags',
      'co_freevars',
      'co_kwonlyargcount',
      'co_lnotab',
      'co_name',
      'co_names',
      'co_nlocals',
      'co_posonlyargcount',
      'co_stacksize',
      'co_varnames']
    attrsj = '\n'.join(attrs)
    print(attrsj)
    return attrs

  def get_attributes(self,f):
    if f:
      attrs = self.attributes(verbose=False)
      d = {k:getattr(f,k) for k in attrs}
      for k,v in d.items():
        print(f"{k}={v}")
    else:
      raise Exception
