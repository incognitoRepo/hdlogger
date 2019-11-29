v_ytd_path='/Users/alberthan/VSCodeProjects/vytd/'

fd -d 1 'el[0-9]{3}' $v_ytd_path | xargs rm
fd -d 1 'hc[0-9]{3}' '/Users/alberthan/VSCodeProjects/vytd/' | xargs rm
fd -d 1 'ydl[0-9]{3}' '/Users/alberthan/VSCodeProjects/vytd/' | xargs rm
fd -d 1 . '/Users/alberthan/VSCodeProjects/vytd/src/youtube-dl/eventpickle' | xargs rm
rm -f '/Users/alberthan/VSCodeProjects/vytd/tb.log'
rm -f '/Users/alberthan/VSCodeProjects/vytd/bfs.log'
rm -f '/Users/alberthan/VSCodeProjects/vytd/auto_repr_err.log'
# rm -f /Users/alberthan/VSCodeProjects/vytd/src/youtube-dl/custom/attribute_err.log
# rm -f /Users/alberthan/VSCodeProjects/vytd/src/youtube-dl/custom/type_err.log
print $(whence -p youtube-dl)
print $(whence -p python3)

ytdl_path='/Users/alberthan/VSCodeProjects/vytd/src/youtube-dl'
# CFG="reference"
if [[ "$pwd" != $ytdl_path ]]; then
  cd $ytdl_path
  python3 -m youtube_dl https://www.youtube.com/watch\?v\=f2exP40AZ6c
  cd -
else
  python3 -m youtube_dl https://www.youtube.com/watch\?v\=f2exP40AZ6c
fi


