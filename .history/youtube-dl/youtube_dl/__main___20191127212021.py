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
import hunter
from youtube_dl.hunterconfig import QueryConfig
from prettyprinter import cpprint
from hunter.tracer import Tracer
from pathlib import Path
from pdb import set_trace as st
import os, io, stackprinter
import pickle, sys
from optparse import OptionParser
from types import GeneratorType
from ansi2html import Ansi2HTMLConverter
from contextlib import contextmanager

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
  return "\n".join(container)

def main2():
  import sys
  import os
  sys.path.insert(0, '/Users/alberthan/VSCodeProjects/HDLogger')
  from hdlogger.tracers import hdTracer
  hd_tracer = hdTracer()
  with captured_output() as (out,err):
    try:
      hd_tracer.run(youtube_dl.main)
    except:
      s = stackprinter.format(sys.exc_info())
      with open('hdlog.err.log','w') as f: f.write(s)
  # from ipdb import set_trace as st; st()
  return_values = hd_tracer.return_values
  serialized_as_hex = hd_tracer.serialized_data
  serialized_as_bytes = [bytes.fromhex(elm) for elm in serialized_as_hex]
  deserialized_to_pyobj = [pickle.loads(elm) for elm in serialized_as_bytes]
  deserialized = hd_tracer.deserialize(hd_tracer.serialized_data)
  output = "\n".join( out.getvalue().splitlines() )

  write_file(join_as_str(return_values),'return_values')
  write_file(join_as_str(serialized_as_hex),'serialized_as_hex')
  write_file(join_as_str(deserialized_to_pyobj),'deserialized_to_pyobj')
  write_file(join_as_str(deserialized),'deserialized')
  write_file(join_as_str(output),'output')

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
      with open('hdlog.err.log','w') as f:
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


# if __name__ == '__main__':
#   print(f"\x1b[0;36m{youtube_dl}\x1b[0m")
#   qc = QueryConfig()
#   qcfg = qc.eventpickle()
#   tracer = Tracer()
#   query,actions,outputs,filenames,write_func,epdf_pklpth = qcfg
#   filename = filenames[0]
#   action = actions[0]
#   if output:
#     output = io.StringIO()
#     action._stream = output
#   tracer.trace(query)
#   try:
#     youtube_dl.main()
#   except SystemExit:
#     tb1 = stackprinter.format(sys.exc_info())
#     try:
#       tracer.stop()
#       if output:
#         outval = output.getvalue()
#         conv = Ansi2HTMLConverter()
#         html = conv.convert(outval)
#         output.close()
#         with open(outvalpth:=filename.parent.joinpath('output.log'),'w') as f:
#           f.write(outval)
#           print(f"wrote output value to {outvalpth}")
#         with open(htmlpth:=filename.parent.joinpath('output.html'),'w') as f:
#           f.write(html)
#           print(f"wrote html output to {htmlpth}")
#       # evt_dcts = action.read_json()
#       # dcts.append(evt_dcts)
#     except BaseException as exc:
#       tb2 = stackprinter.format(exc)
#       with open('tb_inner.log','w') as f:
#         f.write(tb1)
#         f.write(tb2)
#       print("failed_inner")
#   except:
#     with open('tb_outer.log','w') as f:
#       f.write(stackprinter.format(sys.exc_info()))
#     print("failed_outer")
