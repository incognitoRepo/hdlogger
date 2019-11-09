def main():
  import argparse

  parser = argparse.ArgumentParser()
  parser.add_argument('--version', action='version', version='trace 2.0')

  grp = parser.add_argument_group('Main options',
      'One of these (or --report) must be given')

  grp.add_argument('-c', '--count', action='store_true',
      help='Count the number of times each line is executed and write '
                 'the counts to <module>.cover for each module executed, in '
                 'the module\'s directory. See also --coverdir, --file, '
                 '--no-report below.')
  grp.add_argument('-t', '--trace', action='store_true',
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

  t = Trace(opts.count, opts.trace, countfuncs=opts.listfuncs,
              countcallers=opts.trackcalls, ignoremods=opts.ignore_module,
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
