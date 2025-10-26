ffmpeg -i C0012.MP4 -ss 00:00:32 -c copy -y talk6-seg1.mp4
ffmpeg -f concat -i talk6-videos.txt -y talk6-seg-all.mp4
