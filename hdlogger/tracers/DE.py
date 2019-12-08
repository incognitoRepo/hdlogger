

class TraceProcessor:
  def __init__(self,filepath):
    self.pickleable_states = []
    self.pickled_states_as_hex = []
    self.pickled_states_as_bytes = []
    self.dataframe = []
    self.initialize(filepath)

  def initialize(self,filepath):
    path = Path(filepath)
    lines = rf(path,"r").readlines()
    for line in lines:
      _as_hex,_as_bytes = line,bytes.fromhex(line)
      self.pickled_states_as_hex.append(_as_hex)
      self.pickled_states_as_bytes.append(_as_bytes)
      self.pickleable_states.append(pickle.loads(pickle.loads(_as_bytes)))


filepath = '/Users/alberthan/VSCodeProjects/HDLogger/youtube-dl/logs/03.pickled_states_hex.tracer.log'
tp = TraceProcessor(filepath)
