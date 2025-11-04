./master-talk-video.py aosp-1.json
./master-talk-video.py aosp-2.json
./master-talk-video.py open-hardware.json
./master-talk-video.py foss-in-science-1.json
./master-talk-video.py foss-in-science-2.json
./master-talk-video.py open-data-1.json
./master-talk-video.py open-data-2.json

cd compilers
for idx in `seq 1 7`; do 
  echo $idx;
  sh talk-proc.sh C000$idx.MP4
done
sh clip-talk-5.sh

cd ../policy
for idx in `seq 1 6`; do 
  echo $idx;
  sh cut-$idx
  sh talk-proc.sh talk$idx-seg.mp4
done
