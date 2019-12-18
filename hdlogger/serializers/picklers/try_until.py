from hdlogger.utils import *


from typing import Union, Any
class TryUntil:
  def __init__(self,funcs,args):
    self.funcs = funcs
    self.args = args

  def lowest(self,func,arg) -> Union[type(False),Any]:
    try:
      rv = func(arg)
    except:
      return False, wf(stackprinter.format(sys.exc_info()),'logs/tryuntil.log', 'w')
    else:
      return True, func(arg)

  def get_first(self):
    l = []
    for func in self.funcs:
      flag,rv = self.lowest(func,self.args)
      if flag:
        l.append((func,rv))
        return l
      l.append((func,rv))
    return l


def f1(arg):
  1/0

def f2(arg):
  1 + 'a'

def f3(arg):
  print(arg)
  return f"432333{arg}"

def f4(arg):
  return 'aq'

fs = [f1,f2,f3,f4]

args = ['memes']
tu = TryUntil(fs, args)
from ipdb import set_trace as st;st()
print(tu)
