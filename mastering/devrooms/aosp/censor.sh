# Trim a bit of talk that violates CoC
SRC=../mix/aosp/aosp-6.mp4
ffmpeg -i $SRC -t 00:01:34 -y aosp-6-seg1.mp4
ffmpeg -i $SRC -ss 00:02:02 -y aosp-6-seg2.mp4
echo "file 'aosp-6-seg1.mp4'" > filelist;
echo "file 'aosp-6-seg2.mp4'" >> filelist;
wait;
ffmpeg -f concat -i filelist -y final-aosp-6.mp4;
