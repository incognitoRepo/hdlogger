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

[

    '/Users/alberthan/VSCodeProjects/hdlogger/lib/python3.8/site-packages',
    '/Users/alberthan/VSCodeProjects/hdlogger',
    '/Users/alberthan/VSCodeProjects/hdlogger/src/coverage',
    '/Users/alberthan/VSCodeProjects/hdlogger/src/smiley',
    '/Users/alberthan/VSCodeProjects/hdlogger/src/monkeytype',
    '/Users/alberthan/VSCodeProjects/hdlogger/src/pyinstrument',
    '/Users/alberthan/VSCodeProjects/hdlogger/src/py-spy',
    '/Users/alberthan/VSCodeProjects/hdlogger/src/snoop',
    '/Users/alberthan/VSCodeProjects/hdlogger/lib/python3.8/site-packages/'
        'Autologging-1.3.2-py3.8.egg',
    '/Users/alberthan/VSCodeProjects/hdlogger/src/hunter/src'
]
