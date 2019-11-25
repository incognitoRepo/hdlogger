tracers=(
  trace #stdlib
  coverage
  hunter

)

python -m trace --count -C . somefile.py ...
