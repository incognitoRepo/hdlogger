#!/Users/alberthan/VSCodeProjects/vytd/bin/ python3
from __future__ import unicode_literals

# Execute with
# $ python youtube_dl/__main__.py (2.6+)
# $ python -m youtube_dl          (2.7+)

import sys

if __package__ is None and not hasattr(sys, 'frozen'):
  # direct call of __main__.py
  import os.path
  path = os.path.realpath(os.path.abspath(__file__))
  sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

import youtube_dl
import hunter, faulthandler
from youtube_dl.hunterconfig import QueryConfig
from prettyprinter import cpprint, pformat
from hunter.tracer import Tracer
from pathlib import Path
from ipdb import set_trace as st
import os, io, stackprinter
import pickle, sys
from optparse import OptionParser
from types import GeneratorType
from ansi2html import Ansi2HTMLConverter
from contextlib import contextmanager

faulthandler.enable()
test = True
output = True
dcts = []

@contextmanager
def captured_output():
  new_out, new_err = io.StringIO(), io.StringIO()
  old_out, old_err = sys.stdout, sys.stderr
  try:
    sys.stdout, sys.stderr = new_out, new_err
    yield sys.stdout, sys.stderr
  finally:
    sys.stdout, sys.stderr = old_out, old_err

def write_file(string,filename,mode="w"):
  with open(filename,mode) as f:
    f.write(string)

def join_as_str(container):
  container = [str(elm) if isinstance(elm,bytes) else elm for elm in container]
  return "\n".join(container)

def main2():
  import sys
  import os
  sys.path.insert(0, '/Users/alberthan/VSCodeProjects/HDLogger')
  from hdlogger.tracers import hdTracer
  hd_tracer = hdTracer()
  try:
    with captured_output() as (out,err):
      sys.settrace(hd_tracer.trace_dispatch)
      youtube_dl.main()
      sys.settrace(None)
  except SystemExit as e:
    sys.settrace(None)
    print('-- expected SystemExit')
    print(stackprinter.format(sys.exc_info()))
  except:
    sys.settrace(None)
    s = stackprinter.format(sys.exc_info())
    with open('logs/main.exc.log','a') as f: f.write(s)
    raise
  finally:
    sys.settrace(None)
    output = out.getvalue()
    write_file(output,'logs/output.main.log',mode="a")
    df = hd_tracer.make_dataframe()
    hd_tracer.save_history()
    assert hd_tracer.load_history()
    print(df.head())
    from pdb import set_trace as st; st()

def main1():
  import sys
  import os
  sys.path.insert(0, '/Users/alberthan/VSCodeProjects/HDLogger')
  from hdlogger.tracers import hdTracer
  return_value = ""
  hd_tracer = hdTracer()
  with captured_output() as (out,err):
    try:
      return_value = hd_tracer.run(youtube_dl.main)
    except:
      s = stackprinter.format(sys.exc_info())
      with open('log/hdlog.main.log','w') as f:
        f.write(s)
  output = out.getvalue().splitlines()
  with open('hdlog.log','w') as f:
    f.write(
      "HDLOGGER\n========n"
      + "return_value: " + repr(return_value)
      + "trace\n-----" + "\n".join(output)
    )



if __name__ == '__main__':
  main2()

