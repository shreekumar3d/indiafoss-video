# Devroom Video Remastering for IndiaFOSS 2025

We had Sony FX3 cameras recording the devrooms (2 of them). The HDMI output was used
for the livestream.  Cameras also recorded local 1080p videos.  The livestream
captured the slides (didn't happen in 2 devrooms - as we couldn't livestream them).

The videos have been "remastered" to make nicer videos:

- Improved audio quality by reducing noise. Uses sox denoising.
- Better video mixing.  The camera video is used in the intro of the speaker so
  that the viewers get a good look at the speaker.  Later the screen transitions
  to speaker+slides
- Better presentation for online viewing.  Some talks have multiple transitions,
  especially where the presenter shows physical objects.

This repository does not store the source videos and the template images for the
livestream. Those have to be obtained separately to run the scripts.

## Remastering process

Each devroom has one (or more) json file(s) that describes how the talk videos
have to be extracted and processed from the source videos.

To process a specific talk, run:

    $ python3 master-talk-video.py aosp-2.json --index 8

To process all the talks in a devroom, run:

    $ python3 master-talk-video.py open-hardware.json

Each devroom directory also has scripts that show how the videos tracks were
aligned, and denoised.
