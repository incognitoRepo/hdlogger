tracers=(
  trace #stdlib
  coverage
  hunter

)



path=(
  /Users/alberthan/VSCodeProjects/vytd/bin
  $path
)
python3 -m trace --count --trace --module -C . youtube_dl https://www.youtube.com/watch\?v\=f2exP40AZ6c

