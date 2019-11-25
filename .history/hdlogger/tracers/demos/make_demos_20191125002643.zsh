tracers=(
  trace #stdlib
  coverage
  hunter

)

python -m trace --count --trace --module -C ./demos somefile.py ...
