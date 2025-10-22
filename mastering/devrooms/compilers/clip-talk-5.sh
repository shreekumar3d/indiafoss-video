# There was an internet connection drop in talk 5. So we're
# trimming a bit to skip it from 00:11:25 to 00:12:43
#

ffmpeg -i final-C0005.MP4 -t 00:11:25 -c copy -y talk5-seg1.mp4
ffmpeg -i final-C0005.MP4 -ss 00:12:43 -c copy -y talk5-seg2.mp4
echo "file 'talk5-seg1.mp4'" > filelist;
echo "file 'talk5-seg2.mp4'" >> filelist;
wait;
ffmpeg -f concat -i filelist -y final-talk5.mp4;
