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

procam_offset = timedelta( seconds=12, milliseconds=872)
devroom = 'open-hardware'
vid_slides = f'{devroom}/localrec.mkv'
vid_procam = f'{devroom}/procam.mp4'
fullscreen_template = 'overlay-video-full-screen.png'
nr_factor ='0.2' # Amount of NR

# Iterative development flag
skip_proc = False

def set_skip_proc(state):
    global skip_proc
    skip_proc = state

def add_proc(cmd, capture_output=False):
    global skip_proc
    if skip_proc:
        return None
    if capture_output:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result
    else:
        subprocess.run(cmd, check=True)
        print(cmd[-1])

def master_video(vinfo):
    talk_idx = vinfo[0]
    info_image = vinfo[1]
    start1 = vinfo[2]
    intro_end = vinfo[3]
    seg_end = vinfo[4]

    t_start1 = datetime.strptime(start1, '%H:%M:%S')
    intro_end = datetime.strptime(intro_end, '%H:%M:%S')
    seg_end = datetime.strptime(seg_end, '%H:%M:%S')
    duration = seg_end-t_start1
    duration = str(duration)
    intro_dur = intro_end-t_start1
    intro_dur = intro_dur.seconds

    t_start2 = t_start1 + procam_offset
    t_start1 = t_start1.strftime('%H:%M:%S.%f')[:-3]
    t_start2 = t_start2.strftime('%H:%M:%S.%f')[:-3]
    seg_end = seg_end.strftime('%H:%M:%S')
    print('Talk ', talk_idx)
    print('  Start : sv=', t_start1, ' procam=', t_start2)
    print('  Length:', duration)
    print('  Intro :', intro_dur, 'seconds')

    tpath = Path(f'mix/{devroom}/{talk_idx}')
    fpath = Path(f'mix/{devroom}')
    tpath.mkdir( parents=True, exist_ok=True)

    noise_profile = f'{devroom}/procam-noise-profile'

    # MP4 av suffix means the file has both a/v
    # otherwise only video
    seg_vid_slides = f'{tpath}/seg_vid_slides.mp4'
    seg_procam_av = f'{tpath}/seg_procam.mp4'
    seg_procam_a = f'{tpath}/seg_procam.wav'
    seg_procam_nn_a = f'{tpath}/seg_procam_nn.wav'
    seg_speaker_only = f'{tpath}/seg_speaker_only.mp4'
    seg_vid_slides_realign = f'{tpath}/seg_vid_slides_realign.mp4'
    seg_interleaved = f'{tpath}/seg_interleaved.mp4'
    seg_filtered_a = f'{tpath}/filtered_a.wav'
    seg_corrected_a = f'{tpath}/corrected_a.wav'
    seg_talk_av = f'{fpath}/{devroom}-{talk_idx}.mp4'

    set_skip_proc(True)
    set_skip_proc(False)

    # Cut out a segment (of interest) of the two source videos
    # no audio needed from livestream
    add_proc(['ffmpeg', '-i', vid_slides, '-ss', t_start1, '-t', duration, '-an', '-c:v', 'copy', '-y', seg_vid_slides])
    add_proc(['ffmpeg', '-i', vid_procam, '-ss', t_start2, '-t', duration, '-c', 'copy', '-y', seg_procam_av])

    # Cut out the segment - combined with the fullscreen template
    add_proc(['ffmpeg', '-i', seg_procam_av, '-i', fullscreen_template, '-an',
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
    add_proc(['ffmpeg', '-i', info_image, '-i', seg_vid_slides, '-i', seg_procam_av,
              '-filter_complex',
              slides +
              video +
              mix_slides +
              mix_video,
              '-map', '[outv]',
              '-y', seg_vid_slides_realign
    ])

    # Interleave fullscreen video and OBS templated video
    # First few seconds of fullscreen makes thing a bit interesting
    # and give the viewers a good idea of who the speaker is,
    # plus serves well to capture the intro bits
    fs_video = f'[0:v]trim=0:{intro_dur},setpts=PTS-STARTPTS[v0];'
    pres_video = f'[1:v]trim={intro_dur},setpts=PTS-STARTPTS[v1];'
    interleave = '[v0][v1]concat=n=2:v=1:[outv]'
    add_proc(['ffmpeg', '-i', seg_speaker_only, '-i', seg_vid_slides_realign,
              '-filter_complex',
              fs_video +
              pres_video +
              interleave,
              '-map', '[outv]',
              '-y', seg_interleaved
    ])

    # Extract only the audio
    add_proc(['ffmpeg',
              '-i', seg_procam_av,
              '-vn',
              '-acodec', 'pcm_s16le',
              '-y', seg_procam_a
    ])

    # Denoise audio using existing profile
    add_proc(['sox',
              '--multi-threaded',
              seg_procam_a, seg_procam_nn_a,
              'noisered', noise_profile,
              nr_factor
    ])

    # camera audio is mono - replicate in both L/R for better
    # volume
    add_proc(['ffmpeg',
              '-i', seg_procam_nn_a,
              '-af', 'pan=stereo|FL=FL|FR=FL',
              '-acodec', 'pcm_s16le',
              '-y', seg_filtered_a
    ])

    # Measure audio characteristics using loudnorm
    result = add_proc(['ffmpeg',
                       '-i', seg_filtered_a,
                       '-filter:a', 'loudnorm=print_format=json',
                       '-f', 'null', '/dev/null'
                      ],
                      capture_output = True
                     )
    #print(result.stderr)
    #open('/tmp/info','w').write(result.stderr)
    #set_skip_proc(False)
    #output = open('/tmp/info','r').read()

    if result:
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
        add_proc(['ffmpeg',
                  '-i', seg_filtered_a,
                  '-af',
                  f'loudnorm={loudnorm}',
                  '-ar', '48000', # loudnorm upsamples to 96kHz+
                  '-y', seg_corrected_a
        ])

    # Add corrected audio to interleaved slide video
    add_proc(['ffmpeg',
              '-i', seg_interleaved,
              '-i', seg_corrected_a,
              '-map', '0:v:0',
              '-map', '1:a:0',
              '-y', seg_talk_av
    ])

talk2 = ( 2,
     '../../obs/track-ordered/hardware/02_Jigita_jump_to_soldering.png',
     '00:05:17', '00:05:27', '00:35:28'
)
talk3 = ( 3,
     '../../obs/track-ordered/hardware/03_VoltQuest_Open_Source_Hardware_Gaming.png',
     '00:35:44', '00:37:35', '00:52:32'
)
talk4 = ( 4,
     '../../obs/track-ordered/hardware/04_Homelabbing_with_bare_metal.png',
     '00:58:30', '01:00:00', '01:39:30'
)
talk5 = ( 5,
     '../../obs/track-ordered/hardware/05_CoryDora_A_Macropad_A_Supply.png',
     '01:40:00', '01:40:42', '02:09:37'
)
talk6 = ( 6,
     '../../obs/track-ordered/hardware/06_Makerville_Badge.png',
     '02:11:50', '02:12:00', '02:37:36'
)
talk7 = ( 7,
     '../../obs/track-ordered/hardware/07_Because_Glancing_at_Your_Phone.png',
     '02:38:40', '02:39:06', '02:57:05'
)

master_video(talk2)
master_video(talk3)
master_video(talk4)
master_video(talk5)
master_video(talk6)
master_video(talk7)
