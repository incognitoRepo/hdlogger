tracers=(
  trace #stdlib
  coverage
  hunter

)



path=(
  '/Users/alberthan/VSCodeProjects/vytd/src/youtube-dl/youtube_dl'
  $path
)
print $path
python3 -m trace --count --trace --module -C . youtube_dl https://www.youtube.com/watch\?v\=f2exP40AZ6c

youtube-dl
[
    '',
    '/Users/alberthan/VSCodeProjects/tester',
    '/Library/Frameworks/Python.framework/Versions/3.8/lib/python38.zip',
    '/Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8',
    '/Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/lib-'
        'dynload',
    '/Users/alberthan/VSCodeProjects/vytd/lib/python3.8/site-packages',
    '/Users/alberthan/VSCodeProjects/vytd/src/youtube-dl',
    '/Users/alberthan/VSCodeProjects/vytd/src/wcwidth'
]
