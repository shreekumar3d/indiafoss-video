# devroom livestream videos are SD. upscale for now to 1080p to keep changes to a
# minimum
ffmpeg -i ytlive.mp4 -an -vf scale=1920:1080:flags=lanczos -y ytlive-rescale-hd.mp4
