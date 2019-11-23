# -*- coding: utf-8 -*-
# vscode-fold=1
import dis, sys, inspect, trace
from linecache import getline
from ipdb import set_trace as st
from itertools import tee
from types import GeneratorType
import inspect, ctypes
from pygments import highlight
from pygments.lexers import Python3Lexer
from pygments.formatters import Terminal256Formatter
from pygments.styles import get_style_by_name
from pprint import pprint
from .helpers import (
  get_answer,
  Event,
  get_strs,
  get_tracer_kill_pack,
  filter_only,
  Tracer,
)

def get_hmm():
  """Get a thought."""
  return 'hmmm...'

def hmm():
  """Contemplation..."""
  if get_answer():
    print(get_hmm())

class StopTracer(Exception):
  pass

counter0 = 0
def trace_hook_callback0(frame,event,arg):
  global counter0
  counter0 += 1
  if counter0 >= 5:
    sys.settrace(None)
    return None
  return

counter1 = 0
def trace_hook_callback1(frame,event,arg):
  """used in tester.stop_trace1
      stops when counter hits 10
  """
  global counter1
  counter1 += 1
  pkd_frm_strs = get_strs(frame,counter1)
  tkp = get_tracer_kill_pack()
  t = sys.gettrace()
  if counter1 >= 10:
    sys.settrace(None)
    raise StopTracer
  return

counter2 = 0
def trace_hook_callback2(frame,event,arg):
  """used in tester.stop_trace1
      stops when counter hits 10
  """
  global counter2, modules2
  evt = Event(frame,event,arg,collect_data='module')
  if not filter_only(evt.module,['hdlogger','tester']): return
  counter2 += 1
  if event == 'kill':
    sys.settrace(None)
    with open('_trace2.log','a') as f:
      f.write(f"{evt.data}")
      return evt.data
  return trace_hook_callback2

def thcb_evt0(frame,event,arg):
  evt = Event(frame,event,arg,
    collect_data='module')
  if not filter_only(evt.module,['hdlogger','tester']): return
  if event == 'kill':
    sys.settrace(None)
    with open('_thcb_evt0.log','a') as f:
      f.write(f"{evt.data}")
    return 'killed_evt0'
  return thcb_evt0

def thcb_evt1(frame,event,arg):
  """added write_data method to Event"""
  evt = Event(frame,event,arg,
    collect_data='module')
  if not filter_only(evt.module,['hdlogger','tester']): return
  if event == 'kill':
    sys.settrace(None)
    return evt.write_data()
  return thcb_evt1

def thcb_gen0(frame,event,arg):
  evt = Event(frame,event,arg,
    collect_data='module')
  if not filter_only(evt.module,['hdlogger','tester']): return
  if event == 'kill':
    sys.settrace(None)
    return 'killed_gen0'
  return thcb_gen0

def thcb_gen1(frame,event,arg):
  """added write_data method to Event"""
  evt = Event(frame,event,arg,
    write_flag=True,
    collect_data=False)
  if not filter_only(evt.module,['hdlogger','tester']): return
  if event == 'kill':
    sys.settrace(None)
    return evt.write_trace()
  return thcb_gen1

def thcb_gen2b(frame,event,arg):
  idt = " " * 12
  module = frame.f_globals.get('__name__','')
  if not filter_only(module,['tester']):
    sys.settrace(None)
    return
  print()
  if event == 'call':
    print(f"{idt[:-1]}\x1b[1;31mc\x1b[0m: {arg=}")
    local_call(frame,event,arg,thcb_gen2b)
    return thcb_gen2b
  elif event == 'return':
    """if i return first, the generator is preserved
    but if i use the generator here in the tracefunc
    it will never reach its intended usage"""
    # return
    print(f"{idt[:-1]}\x1b[1;33mr\x1b[0m: {arg=}") # just printing arg is fine
    local_ret(frame,event,arg,thcb_gen2b)
    return
  elif event == 'line':
    print(f"{idt[:-1]}\x1b[1;32ml\x1b[0m: {arg=}")
    return local_line
  elif event == 'exception':
    print(f"{idt[:-1]}\x1b[1;34me\x1b[0m: {arg=}")
    evt = Event(frame,event,arg,
      write_flag=True,
      collect_data=False)
    return local_exc
  elif event == 'opcode':
    print(f"{idt[:-1]}\x1b[1;35mo\x1b[0m: {arg=}")
    evt = Event(frame,event,arg,
      write_flag=True,
      collect_data=False)
    return local_op
  evt = Event(frame,event,arg,
    write_flag=True,
    collect_data=False)
  print('c1 ',end="")
  print('c2 ')

def local_call(frame,event,arg,func):
  evt = Event(frame,event,arg,
    write_flag=True,
    collect_data=False)
  print("  \x1b[0;31mlocal_call\x1b[0m:",f"{arg=}")
  rf1,rf2,rf3 = func,local_call,None
  return rf1

def local_line(frame,event,arg):
  # Event here: arg=something
  evt = Event(frame,event,arg,
      write_flag=False,
      collect_data=False)
  print("  \x1b[0;32mlocal_line\x1b[0m:",f"{arg=}")
  rf1,rf2,rf3 = None,local_line,None
  return rf1

def local_ret(frame,event,arg):
  # list(arg) works here if put first (aka b4 global)
  # doesnt matter whats returned here, returning nothing works too
  # print(list(arg)); print(list(frame.f_locals['rv']))
  d = locals()
  dks = d.keys()
  type_val_pairs = []
  for k in dks:
    print(f"{' '*11}d: {k}={d[k]}({type(d[k])})")
    if isinstance(d[k],GeneratorType):
      print(arg) # gen2b ok
      print(list(arg)) # gen2c exhausts generator
      # [elm for elm in arg] cannot iterate over generatoir
      print(inspect.getgeneratorstate(arg))
      print(inspect.getgeneratorlocals(arg))

  print("   \x1b[0;33mlocal_ret\x1b[0m:",f"{arg=}")
  # rf1,rf2,rf3 = func,local_ret,None
  # return

def local_exc(frame,event,arg):
  print("  \x1b[1;34mlocal_exc\x1b[0m",f"{arg=}")
  rf1,rf2,rf3 = func,local_exc,None
  return rf3

def local_op(frame,event,arg):
  print("  \x1b[1;35mlocal_op\x1b[0m",f"{arg=}")
  rf1,rf2,rf3 = func,local_op,None
  return rf3

counter3a = 0
def thcb_gen2a(frame,event,arg):
  global counter3a
  src = getline(frame.f_code.co_filename,frame.f_lineno,frame.f_globals)
  srchld = highlight(src,Python3Lexer(),Terminal256Formatter(style=get_style_by_name('monokai')))
  this_func = "\x1b[2;3;96mthcb_gen2\x1b[0m"
  print(f"in {this_func}: {counter3a=}, {event=}, {arg=}")
  print(f"            : {frame.f_lineno:<03} {srchld}",end="")
  counter3a += 1
  if counter3a >= 10:
    sys.settrace(None)
    return
  if event == 'call':
    # global trace
    print("  \x1b[1;31mc\x1b[0m",f"{arg=}")
    # return local_call
  elif event == 'line':
    # local trace, arg=None, returns local trace func
    print("  \x1b[1;32ml\x1b[0m",f"{arg=}")
    # print(local_line(frame,event,arg))
    return local_line
  elif event == 'return':
    # local trace, returns ignored
    print("  \x1b[1;33mr\x1b[0m",f"{arg=}")
    return local_ret
  elif event == 'exception':
    # local trace, arg=tuple(exception,value,tb),returns new local trace func
    print("  \x1b[1;34me\x1b[0m",f"{arg=}")
    return local_exc
  elif event == 'opcode':
    # local trace, arg=None,returns new local trace func
    print("  \x1b[1;35mo\x1b[0m",f"{arg=}")
    return local_op
  # if isinstance(arg,GeneratorType) or inspect.isgeneratorfunction(arg):
  #   arg,arg2 = tee(arg)
  #   evt = Event(frame,event,arg2,
  #     write_flag=True,
  #     collect_data='arg')
  print('c1')
  evt = Event(frame,event,arg,
    write_flag=True,
    collect_data=False)
  print('c2')
  if not filter_only(evt.module,['tester']): return
  print('c4')
  if event == 'kill':
    print('c5')
    sys.settrace(None)
    print('c6')
    return
  return thcb_gen2

counter3 = 0
def thcb_gen2(frame,event,arg):
  global counter3
  src = getline(frame.f_code.co_filename,frame.f_lineno,frame.f_globals)
  srchld = highlight(src,Python3Lexer(),Terminal256Formatter(style=get_style_by_name('monokai')))
  this_func = "\x1b[2;3;96mthcb_gen2\x1b[0m"
  this_loco = "\x1b[2;3;97m   locals\x1b[0m"
  idt = " " * 12
  print(f"\nin {this_func}: {counter3=}, {event=}, {arg=}")
  print(f"   {this_loco}: {frame.f_locals.keys()}")
  print(f"{idt[:-4]}{frame.f_lineno:>4}: {srchld}",end="")
  counter3 += 1
  # if counter3 >= 10:
  #   sys.settrace(None)
  #   return
  module = frame.f_globals.get('__name__','')
  if not filter_only(module,['hdlogger','tester']):
    sys.settrace(None)
    return
  if event == 'call':
    # global trace
    print(f"{idt[:-1]}\x1b[1;31mc\x1b[0m: {arg=}")
    # return thcb_gen2 : local_line for every line event, except last
    # return local_call: local_line for return event and line event b4 return event
    # return None      : no local_line
    # no return        : no local_line
    # no return + return thcb_gen2 : l_l for every line event, except last
    local_call(frame,event,arg,thcb_gen2)
    return thcb_gen2
  elif event == 'return':
    # local trace, returns ignored
    # generator ultimately returns if return @ start
    # doesn't matter what is returned here, but should return to stop global
    # list(arg) works here, if put first (aka b4 local)
    # print(list(arg))
    print(arg); return
    print(f"{idt[:-1]}\x1b[1;33mr\x1b[0m: {arg=}")
    local_ret(frame,event,arg)
    return
  elif event == 'line':
    # local trace, arg=None, returns local trace func
    # Event here: arg = None
    print(f"{idt[:-1]}\x1b[1;32ml\x1b[0m: {arg=}")
    # local_line(frame,event,arg)
    return local_line
  elif event == 'exception':
    # local trace, arg=tuple(exception,value,tb),returns new local trace func
    print(f"{idt[:-1]}\x1b[1;34me\x1b[0m: {arg=}")
    evt = Event(frame,event,arg,
      write_flag=True,
      collect_data=False)
    return local_exc
  elif event == 'opcode':
    # local trace, arg=None,returns new local trace func
    print(f"{idt[:-1]}\x1b[1;35mo\x1b[0m: {arg=}")
    evt = Event(frame,event,arg,
      write_flag=True,
      collect_data=False)
    return local_op
  evt = Event(frame,event,arg,
    write_flag=True,
    collect_data=False)
  print('c1 ',end="")
  print('c2 ')
  # return thcb_gen2

def thcb_gen2c(frame,event,arg):
  tracer = trace.Trace(count=False,trace=True)
  idt = " " * 12
  module = frame.f_globals.get('__name__','')
  if not filter_only(module,['tester']):
    sys.settrace(None)
    return
  print()
  if event == 'call':
    print(f"{idt[:-1]}\x1b[1;31mc\x1b[0m: {arg=}")
    local_call(frame,event,arg,func=thcb_gen2c)
    return thcb_gen2c
  elif event == 'return':
    """if i return first, the generator is preserved
    but if i use the generator here in the tracefunc
    it will never reach its intended usage"""
    # return
    print(f"{idt[:-1]}\x1b[1;33mr\x1b[0m: {arg=}") # just printing arg is fine
    local_ret(frame,event,arg,func=thcb_gen2c)
    return
  elif event == 'line':
    print(f"{idt[:-1]}\x1b[1;32ml\x1b[0m: {arg=}")
    return local_line
  elif event == 'exception':
    print(f"{idt[:-1]}\x1b[1;34me\x1b[0m: {arg=}")
    evt = Event(frame,event,arg,
      write_flag=True,
      collect_data=False)
    return local_exc
  elif event == 'opcode':
    print(f"{idt[:-1]}\x1b[1;35mo\x1b[0m: {arg=}")
    evt = Event(frame,event,arg,
      write_flag=True,
      collect_data=False)
    return local_op
  evt = Event(frame,event,arg,
    write_flag=True,
    collect_data=False)
  print('c1 ',end="")
  print('c2 ')

def thcb_gen2d(frame,event,arg):
  tracer = trace.Tracer(ignoredirs=[sys.base_prefix, sys.base_exec_prefix,])
  tracer.run('main()')
  # make a report, placing output in /tmp
  r = tracer.results()
  r.write_results(show_missing=True, coverdir="/tmp")

def main():
  import argparse
  IGNOREMODS = []
  IGNOREDIRS = []

  parser = argparse.ArgumentParser()
  parser.add_argument('--version', action='version', version='trace 2.0')

  grp = parser.add_argument_group('Main options',
      'One of these (or --report) must be given')

  grp.add_argument('-c', '--count', action='store_true', default=True,
      help='Count the number of times each line is executed and write '
                 'the counts to <module>.cover for each module executed, in '
                 'the module\'s directory. See also --coverdir, --file, '
                 '--no-report below.')
  grp.add_argument('-t', '--trace', action='store_true', default=True,
      help='Print each line to sys.stdout before it is executed')
  grp.add_argument('-l', '--listfuncs', action='store_true',
      help='Keep track of which functions are executed at least once '
                 'and write the results to sys.stdout after the program exits. '
                 'Cannot be specified alongside --trace or --count.')
  grp.add_argument('-T', '--trackcalls', action='store_true',
      help='Keep track of caller/called pairs and write the results to '
                 'sys.stdout after the program exits.')

  grp = parser.add_argument_group('Modifiers')

  _grp = grp.add_mutually_exclusive_group()
  _grp.add_argument('-r', '--report', action='store_true',
      help='Generate a report from a counts file; does not execute any '
                 'code. --file must specify the results file to read, which '
                 'must have been created in a previous run with --count '
                 '--file=FILE')
  _grp.add_argument('-R', '--no-report', action='store_true',
      help='Do not generate the coverage report files. '
                 'Useful if you want to accumulate over several runs.')

  grp.add_argument('-f', '--file',
      help='File to accumulate counts over several runs')
  grp.add_argument('-C', '--coverdir',
      help='Directory where the report files go. The coverage report '
                 'for <package>.<module> will be written to file '
                 '<dir>/<package>/<module>.cover')
  grp.add_argument('-m', '--missing', action='store_true',
      help='Annotate executable lines that were not executed with '
                 '">>>>>> "')
  grp.add_argument('-s', '--summary', action='store_true',
      help='Write a brief summary for each file to sys.stdout. '
                 'Can only be used with --count or --report')
  grp.add_argument('-g', '--timing', action='store_true',
      help='Prefix each line with the time since the program started. '
                 'Only used while tracing')

  grp = parser.add_argument_group('Filters',
      'Can be specified multiple times')
  grp.add_argument('--ignore-module', action='append', default=[],
      help='Ignore the given module(s) and its submodules '
                 '(if it is a package). Accepts comma separated list of '
                 'module names.')
  grp.add_argument('--ignore-dir', action='append', default=[],
      help='Ignore files in the given directory '
                 '(multiple directories can be joined by os.pathsep).')

  parser.add_argument('--module', action='store_true', default=False,
            help='Trace a module. ')
  parser.add_argument('progname', nargs='?',
      help='file to run as main program')
  parser.add_argument('arguments', nargs=argparse.REMAINDER,
      help='arguments to the program')

  opts = parser.parse_args()

  if opts.ignore_dir:
    rel_path = 'lib', 'python{0.major}.{0.minor}'.format(sys.version_info)
    _prefix = os.path.join(sys.base_prefix, *rel_path)
    _exec_prefix = os.path.join(sys.base_exec_prefix, *rel_path)

  def parse_ignore_dir(s):
    s = os.path.expanduser(os.path.expandvars(s))
    s = s.replace('$prefix', _prefix).replace('$exec_prefix', _exec_prefix)
    return os.path.normpath(s)

  opts.ignore_module = [mod.strip()
                          for i in opts.ignore_module for mod in i.split(',')]
  opts.ignore_dir = [parse_ignore_dir(s)
                       for i in opts.ignore_dir for s in i.split(os.pathsep)]

  if opts.report:
    if not opts.file:
      parser.error('-r/--report requires -f/--file')
    results = CoverageResults(infile=opts.file, outfile=opts.file)
    return results.write_results(opts.missing, opts.summary, opts.coverdir)

  if not any([opts.trace, opts.count, opts.listfuncs, opts.trackcalls]):
    parser.error('must specify one of --trace, --count, --report, '
                     '--listfuncs, or --trackcalls')

  if opts.listfuncs and (opts.count or opts.trace):
    parser.error('cannot specify both --listfuncs and (--trace or --count)')

  if opts.summary and not opts.count:
    parser.error('--summary can only be used with --count or --report')

  if opts.progname is None:
    parser.error('progname is missing: required with the main options')

  t = Tracer(ignoremods=opts.ignore_module,
              ignoredirs=opts.ignore_dir, infile=opts.file,
              outfile=opts.file, timing=opts.timing)
  try:
    if opts.module:
      import runpy
      module_name = opts.progname
      mod_name, mod_spec, code = runpy._get_module_details(module_name)
      sys.argv = [code.co_filename, *opts.arguments]
      globs = {
        '__name__': '__main__',
        '__file__': code.co_filename,
        '__package__': mod_spec.parent,
        '__loader__': mod_spec.loader,
        '__spec__': mod_spec,
        '__cached__': None,
      }
    else:
      sys.argv = [opts.progname, *opts.arguments]
      sys.path[0] = os.path.dirname(opts.progname)

      with open(opts.progname) as fp:
        code = compile(fp.read(), opts.progname, 'exec')
      # try to emulate __main__ namespace as much as possible
      globs = {
        '__file__': opts.progname,
        '__name__': '__main__',
        '__package__': None,
        '__cached__': None,
      }
    t.runctx(code, globs, globs)
  except OSError as err:
    sys.exit("Cannot run file %r because: %s" % (sys.argv[0], err))
  except SystemExit:
    pass

  results = t.results()

  if not opts.no_report:
    results.write_results(opts.missing, opts.summary, opts.coverdir)
