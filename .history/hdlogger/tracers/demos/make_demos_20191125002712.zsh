tracers=(
  trace #stdlib
  coverage
  hunter

)

python -m trace --count --trace --module -C . somefile.py ...
