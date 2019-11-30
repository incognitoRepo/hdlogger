v_ytd_path='/Users/alberthan/VSCodeProjects/vytd/'

fd -d 1 'el[0-9]{3}' $v_ytd_path | xargs rm
fd -d 1 'hc[0-9]{3}' '/Users/alberthan/VSCodeProjects/vytd/' | xargs rm
fd -d 1 'ydl[0-9]{3}' '/Users/alberthan/VSCodeProjects/vytd/' | xargs rm
fd -d 1 . '/Users/alberthan/VSCodeProjects/vytd/src/youtube-dl/eventpickle' | xargs rm
rm -f '/Users/alberthan/VSCodeProjects/vytd/tb.log'
rm -f '/Users/alberthan/VSCodeProjects/vytd/bfs.log'
rm -f '/Users/alberthan/VSCodeProjects/vytd/auto_repr_err.log'
rm -f '/Users/alberthan/VSCodeProjects/vytd/src/youtube-dl/logs/*'
# rm -f /Users/alberthan/VSCodeProjects/vytd/src/youtube-dl/custom/attribute_err.log
# rm -f /Users/alberthan/VSCodeProjects/vytd/src/youtube-dl/custom/type_err.log
print $(whence -p youtube-dl)
print $(whence -p python3)

ytdl_path='/Users/alberthan/VSCodeProjects/vytd/src/youtube-dl'
video_url='https://www.pornhub.com/view_video.php?viewkey=ph5de044a26e932'
# CFG="reference"
if [[ "$pwd" != $ytdl_path ]]; then
  cd $ytdl_path
  # python3 -m youtube_dl https://www.youtube.com/watch\?v\=f2exP40AZ6c
  python3 -mipdb -m youtube_dl $video_url
  # python3 -m youtube_dl $video_url
  cd -
else
  python3 -m youtube_dl $video_url
fi


