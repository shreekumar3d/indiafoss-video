#
# master-talk-video.py
#
# Creates "mastered" videos combining livestream videos and
# recordings from a "pro" camera (Sony FX3)
#
# The livestream has slides and speaker video side by side
# The pro camera recording has high res speaker video, and
# much better audio
#
# The two videos have a time offset - which must be found outside
# and plugged in here.
#
# This script does the following:
#
# - Uses the IF25 livestream template
# - Places a rescaled procam video in the place of the
#   speaker video area.
# - Places slides in the slides video area
# - Combines speaker/talk info (used in OBS for scene)
# - Initial parts use the fullscreen speaker video template.
#   which later switches to slides+video
#

from datetime import timedelta
from datetime import datetime
import sys
import subprocess
from pathlib import Path
from pprint import pprint
import re
import json

# First talk
start1 = timedelta( minutes=5, seconds=16)
procam_offset = timedelta( seconds=12, milliseconds=872)
duration = datetime.min + timedelta( minutes=30, seconds=7)
intro_dur = 10
devroom = 'open-hardware'
talk_idx = 2
vid_slides = f'{devroom}/localrec.mkv'
vid_procam = f'{devroom}/procam.mp4'
info_image = '../../obs/track-ordered/hardware/02_Jigita_jump_to_soldering.png'
fullscreen_template = 'overlay-video-full-screen.png'

# Iterative development flag
skip_proc = False

def set_skip_proc(state):
    global skip_proc
    skip_proc = state

def add_proc(args, capture_output=False):
    global skip_proc
    if skip_proc:
        return
    cmd = ['ffmpeg']+args
    if capture_output:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result
    else:
        subprocess.run(cmd)
        print(args[-1])

t_start1 = datetime.min + start1
t_start2 = t_start1 + procam_offset
t_start1 = t_start1.strftime('%H:%M:%S.%3f')[:-3]
t_start2 = t_start2.strftime('%H:%M:%S.%3f')[:-3]
duration = duration.strftime('%M:%S')

tpath = Path(f'mix/{devroom}/{talk_idx}')
fpath = Path(f'mix/{devroom}')
tpath.mkdir( parents=True, exist_ok=True)

seg_vid_slides = f'{tpath}/seg_vid_slides.mp4'
seg_procam = f'{tpath}/seg_procam.mp4'
seg_speaker_only = f'{tpath}/seg_speaker_only.mp4'
seg_vid_slides_realign = f'{tpath}/seg_vid_slides_realign.mp4'
seg_interleaved = f'{tpath}/seg_interleaved.mp4'
seg_afiltered = f'{tpath}/afiltered.mp4'
seg_talk = f'{fpath}/{devroom}-{talk_idx}.mp4'

#set_skip_proc(True)
#set_skip_proc(False)

# Cut out a segment (of interest) of the two source videos
add_proc(['-i', vid_slides, '-ss', t_start1, '-t', duration, '-c', 'copy', '-y', seg_vid_slides])
add_proc(['-i', vid_procam, '-ss', t_start2, '-t', duration, '-c', 'copy', '-y', seg_procam])

# Cut out the segment - combined with the fullscreen template
add_proc(['-i', seg_procam, '-i', fullscreen_template,
          '-filter_complex',
          '[0:v][1:v]overlay=0:0',
          '-y', seg_speaker_only
])

# Create a video that stuffs
#  - procam video
#  - slides
#  - OBS template with speaker info
# into one video
#
slides='[1:v]crop=1568:882:350:1,scale=1436:808[v1];'
video='[2:v]crop=810:1080:555:0,scale=360:480[v2];'
mix_slides='[0:v][v1]overlay=42:124[mix1];'
mix_video='[mix1][v2]overlay=1518:234[outv]'
add_proc(['-i', info_image, '-i', seg_vid_slides, '-i', seg_procam,
          '-filter_complex',
          slides +
          video +
          mix_slides +
          mix_video,
          '-map', '[outv]', '-map', '2:a',
          '-y', seg_vid_slides_realign
])

# Interleave fullscreen video and OBS templated video
# First few seconds of fullscreen makes thing a bit interesting
# and give the viewers a good idea of who the speaker is,
# plus serves well to capture the intro bits
fs_video = f'[0:v]trim=0:{intro_dur},setpts=PTS-STARTPTS[v0];'
pres_video = f'[1:v]trim={intro_dur},setpts=PTS-STARTPTS[v1];'
fs_audio = f'[0:a]atrim=0:{intro_dur},asetpts=PTS-STARTPTS[a0];'
pres_audio = f'[1:a]atrim={intro_dur},asetpts=PTS-STARTPTS[a1];'
interleave = '[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]'
add_proc(['-i', seg_speaker_only, '-i', seg_vid_slides_realign,
          '-filter_complex',
          fs_video +
          pres_video +
          fs_audio +
          pres_audio +
          interleave,
          '-map', '[outv]', '-map', '[outa]',
          '-y', seg_interleaved
])

# Lowpass filter with 3k Hz to get rid of ringing noises
# camera audio is mono - replicate in both L/R for better
# volume
add_proc(['-i', seg_interleaved,
          '-af', 'pan=stereo|FL=FL|FR=FL,lowpass=f=3000',
          '-y', seg_afiltered
])

# Measure audio characteristics using loudnorm
result = add_proc(['-i', seg_afiltered,
                   '-filter:a', 'loudnorm=print_format=json',
                   '-f', 'null', '/dev/null'
                  ],
                  capture_output = True
                 )
#print(result.stderr)
#open('/tmp/info','w').write(result.stderr)
#set_skip_proc(False)
#output = open('/tmp/info','r').read()
output = result.stderr

# Extract measured values and prepare corrections
param = json.loads(re.sub('^.*({.*}).*$','\\1', output, flags=re.DOTALL))
loudnorm = 'linear=true:I=-16:LRA=11:tp=-1.5:'
loudnorm += f'measured_I={param["input_i"]}:'
loudnorm += f'measured_LRA={param["input_lra"]}:'
loudnorm += f'measured_tp={param["input_tp"]}:'
loudnorm += f'measured_thresh={param["input_thresh"]}:'
loudnorm += f'offset={param["target_offset"]}:'
loudnorm += 'print_format=summary'

# Normalize audio volume
# we use level -16 which is technically for podcasts, but not video
# video recommended level is -23, but that turns out to be low
# for desktops and phones - but pretty good for TVs
# (you can see this in the VU meter in audacity)
add_proc(['-i', seg_afiltered,
          '-af',
          f'loudnorm={loudnorm}',
          '-y', seg_talk
])
