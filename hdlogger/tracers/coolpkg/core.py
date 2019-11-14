from pathlib import Path

def gen2d():
  with Path('/Users/alberthan/VSCodeProjects/tester/_jsnpkl.json').resolve() as p:
    if p.exists(): p.unlink()
  tracer = Tracer(ignoredirs=[sys.base_prefix, sys.base_exec_prefix,])
  tracer.run('list(final_selector2())')
  r = tracer.results()
  r.write_results(show_missing=True, coverdir="/tmp")
  return r

def selector_function2():
  for pair in itertools.product('a',range(3,5)):
    yield _merge(pair)

def final_selector2():
  rv = selector_function2()
  # u get a different trace if you print list(rv) here
  # print(f"fs2: {list(rv)=}")
  # cf = currentframe()
  # print(cf.f_locals.keys())
  return rv

def _merge(formats_info):
  return {
    'ltr':formats_info[0],
    'num ':formats_info[1]
  }
