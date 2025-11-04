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
aligned, and denoised. Read on for how.

I also made a script to render all devroom videos just for fund, and to see
how long it takes

    $ time sh render-all-if25-devroom.sh 2>&1 | tee log-render-all
    real    282m25.190s
    user    3953m18.265s
    sys     113m26.113s

Takes less than 5 hrs on my 16 core AMD Ryzen 7950X based desktop.  That's a
multithreading speedup of 14x.

## Source Videos

UNCUT videos from the camera. These cover the speaker, but aren't good for slides.
The livestream serves as the source for slides, except for AOSP (see below).

### AOSP

[Camera UNCUT Part 1](https://youtu.be/3kkF0v3YUEQ)
[Camera UNCUT Part 2](https://youtu.be/zjsKxRnsqvY)

AOSP was livestreamed starting midway, after the livestreaming setup related issues
were resolved. Sahaj from the AOSP devroom made local recordings. Offsets in the
scripts are tied to these files:

[Local recording of Slides Part 1](https://youtu.be/ZOvq5_Wnb94)
[Local recording of Slides Part 2](https://youtu.be/LfZhEB5AlWo)

### Open Hardware

[Camera UNCUT](https://youtu.be/I5SdpU7rxsU)

### FOSS in Science

[Camera UNCUT Part 1](https://youtu.be/WkRojX8djjU)
[Camera UNCUT Part 2](https://youtu.be/_viEFEaVCrQ)

### Open Data

[Camera UNCUT Part 1](https://youtu.be/vbwtAJDrUS8)
[Camera UNCUT Part 2](https://youtu.be/2R21h2wBgOQ)

## Behind the Process

The mastering process is:

* Align the camera video with the livestream (speaker+slides), using the audio
  stream.  This alignment generataes an offset in seconds. If the camera video
  lags, then this should be treated as a negative value, otherwise positive.

  Each devroom directory has a align-audio.py script that captures the steps.
  The duration of audio that needs to be matched differs depending on the case,
  otherwise they are all the same scripts.

* Denoising using sox. For this, locate a segment of audio in the camera video
  with no speech and just noise.  Audacity is good for this.  Then generate
  a noise profile. Apply and check on the audio track.

  Each devroom directory has a denoise-audio.sh script that does this. The
  timestamps were manually generated, and recorded in the scripts.

* Level correct the audio using normalization. We're using an audio level of 
  -16, as opposed to a recommended level of -23/-24.  This is because most
  people who reviewed the audio had their volume level set around 50%.
  Potential reason might be that people hear a lot more audio (podcasts etc),
  and -16 is the recommended level for such things. Setting to -23/-24 makes
  the audios less loud even at max volume, and most people don't have the
  option of overamplification.  This is true for desktops/mobiles, not an
  issue for TVs.  So -16 is good, and isn't a problem for TVs either, as the
  volume can be toned down if it's too loud.

* For one devroom (Data) I also had to apply a lowpass filter to reduce
  some tinny noise. This needs to be investigated later.

* Combine the videos, with a cutlist of timestamps, merge with denoised +
  corrected audio.  (master-talk-video.py)

# Overall learning from Mastering

## Technical

* Record all streams at source... always ! You can always remix later. Slides,
  video, audio.
* Ideally record all audio stream separate, mix on need.
* Don't use any "auto" settings. Be explicit in all technical parameters - e.g.
  youtube livestreaming keys must be set to the resolution needed. "auto" has
  caused SD recordings for the livestream in most cases.
* Need to create a method to run the audio noise characterization upfront,
  Easy to setup and do by anyone.
* Ideally just standardize the audio equipment (and own it!). Just feed it
  downstream to whoever mixes it into the loudspeakers.  That way we are
  insulated from the vagaries of the vendors! Watch out for any electrical
  coupliing issues - that would still create noise if we aren't careful.
  Audio equipment would be cheaper to own than video.
* Point to poinder. Hmmm what if we just went floating point audio !?

## Human/Process

* If the introductions are short, then ask the devrooms to do introduce the
  speaker after the laptop setup is done.  A long gap in the beginning is
  bad for video cuts.

* Improve the presentation infra - standardize cables, include a USB-C converter.
  This may make the above point redundant. Make sure usage of laptop etc is shown
  to devroom volunteers. 

* Spend 10 minutes to train devrooms on how-to run the show. Standardize setup
  instructions and tests. Update documents - do this before the CFP issues :)

# Things I'd rather not talk about

Couple of devrooms (Compilers and Geopolitics+Policy) were recorded with the same
camera.  However, we didn't record the slides.  That's because the video team
got held up in the main/other audis on both days in the morning. 

These devrooms had a TV + laptop + speaker talking into the mic. Room capacity was
about 35-40 people. Sony FX3 recording the proceedings. Technically this
these devrooms were the easiest, but because we went to them last, the only thing
we got out of these devrooms were camera recordings. No external audio to worry
about, and hence no noise cancellation to do.

Long story short, the videos are processed with a fullscreen template overlayed.
Plus audio level correction. Good enough for many of the videos, but some videos
really could do with the slides being visible. The Sony FX3 was chosen for its
great eye focus. But that problem with camera only video - as the slides get
defocussed.  Well, you live and you learn!
