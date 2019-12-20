
import snoop

def type_watch(source, value):
  return 'type({})'.format(source), type(value)

snoop.install(
  out='logs/snoop.log',
  color = False,
  prefix = 'snoop: ',
  columns = ['time','file','function'],
  watch_extras=[type_watch],
  # builtins=False,
)
