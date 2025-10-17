# Reference working full script
set -e
#
# extract full audio track
ffmpeg -i procam-2.mp4 -vn -acodec pcm_s16le -y procam-2-audio.wav
# extract pre-determined silence section (with noise).
ffmpeg -i procam-2-audio.wav -ss 01:03:53 -to 01:03:55 -y procam-2-audio-noise.wav
# do noise profiling
# use 1 second
sox procam-2-audio-noise.wav -n trim 0 1 noiseprof procam-2-noise-profile
# do noise reduction
time sox --multi-threaded procam-2-audio.wav procam-2-audio-nn.wav noisered procam-2-noise-profile 0.2
