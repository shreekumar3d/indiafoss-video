# Reference working full script
set -e
#
# extract full audio track
ffmpeg -i procam.mp4 -vn -acodec pcm_s16le -y procam-audio.wav
# extract pre-determined silence section (with noise).
# Used audacity to find a nice quiet spot just after Anuj's QA - using that for trim
ffmpeg -i procam-audio.wav -ss 02:37:38.939 -to 02:37:40.479 -y procam-audio-noise.wav
# do noise profiling, output:procam-oh_noise_profile
# use 1 second
sox procam-audio-noise.wav -n trim 0 1 noiseprof procam-noise-profile
# do noise reduction - ~2.5 minutes on my desktop (64 core Ryzen 9)
# reasonable results
time sox --multi-threaded procam-audio.wav procam-audio-nn.wav noisered procam-noise-profile 0.2
