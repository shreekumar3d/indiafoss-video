# Reference working full script
set -e
#
# extract full audio track
ffmpeg -i procam-1.mp4 -vn -acodec pcm_s16le -y procam-1-audio.wav
# extract pre-determined silence section (with noise).
# Used audacity to find a nice quiet spot just after Anuj's QA - using that for trim
ffmpeg -i procam-1-audio.wav -ss 00:45:00.500 -to 00:45:01.500 -y procam-1-audio-noise.wav
# do noise profiling
# use 1 second
sox procam-1-audio-noise.wav -n trim 0 1 noiseprof procam-1-noise-profile
# do noise reduction
time sox --multi-threaded procam-1-audio.wav procam-1-audio-nn.wav noisered procam-1-noise-profile 0.2
