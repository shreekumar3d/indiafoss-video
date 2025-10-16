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
    noise_profile = f'{devroom}/procam-noise-profile'

    talk_idx = vinfo[0]
    info_image = vinfo[1]

    tpath = Path(f'mix/{devroom}/{talk_idx}')
    fpath = Path(f'mix/{devroom}')
    tpath.mkdir( parents=True, exist_ok=True)
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


    start_sv = datetime.strptime(vinfo[2], '%H:%M:%S')
    end_sv = datetime.strptime(vinfo[-1], '%H:%M:%S')

    print(vinfo[2:])

    seg_duration = datetime.min + (end_sv-start_sv)
    seg_duration = seg_duration.strftime('%H:%M:%S.%f')[:-3]
    start_procam = start_sv + procam_offset

    t_start_sv = start_sv.strftime('%H:%M:%S.%f')[:-3]
    t_start_procam = start_procam.strftime('%H:%M:%S.%f')[:-3]
    print('Talk ', talk_idx)
    print(f'  Start : sv @ {t_start_sv} procam @ {t_start_procam}')
    print(f'  Length: {seg_duration}')

    overlap = 1 # 1 seconds between clips
    is_first_seg = True
    is_fs_video = True
    seg_idx = 0
    clips = []
    for start_pos, end_pos in zip(vinfo[2:], vinfo[3:]):
        st = datetime.strptime(start_pos, '%H:%M:%S')
        et = datetime.strptime(end_pos, '%H:%M:%S')
        # move start time by the video overlap on the
        # second clip and beyond
        if not is_first_seg:
           st = st - timedelta(seconds=overlap)
        offset_start = st - start_sv
        duration_t = et-st
        duration = datetime.min + duration_t
        duration = duration.strftime('%H:%M:%S.%f')[:-3]
        seg_fname = f'{tpath}/seg-{seg_idx}.mp4'
        input_vfname = seg_speaker_only if is_fs_video else seg_vid_slides_realign
        this_clip = [seg_idx, input_vfname, offset_start, duration, seg_fname]
        print('  clip = ', this_clip)
        clips.append(this_clip)
        is_first_seg = False
        is_fs_video = not is_fs_video # alternate clips
        seg_idx += 1

    set_skip_proc(True)
    set_skip_proc(False)

    # Cut out a segment (of interest) of the two source videos
    # no audio needed from livestream
    add_proc(['ffmpeg', '-i', vid_slides, '-ss', t_start_sv, '-t', seg_duration, '-an', '-c:v', 'copy', '-y', seg_vid_slides])
    add_proc(['ffmpeg', '-i', vid_procam, '-ss', t_start_procam, '-t', seg_duration, '-c', 'copy', '-y', seg_procam_av])

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

    # Generate all the cuts of the video files
    for seg_idx, src_vfile, start, duration, out_vfile in clips:
        add_proc(['ffmpeg',
                  '-i', src_vfile,
                  '-ss', str(start), '-t', duration,
                  '-an',
                  '-y', out_vfile
        ])

    # Merge the cuts into one video with crossfades!
    src_vid = "[0:v]"
    filter_complex = ""
    stitch_cmd = ['ffmpeg']
    stitch_cmd.append('-i')
    stitch_cmd.append(clips[0][-1])
    for seg_idx, src_vfile, start, duration, out_vfile in clips[1:]:
        next_src_vid = f"vfade{seg_idx}"
        filter_complex += f"{src_vid}[{seg_idx}:v]xfade=transition=fade:duration={overlap}:offset={start.seconds}[{next_src_vid}];"
        stitch_cmd.append('-i')
        stitch_cmd.append(out_vfile)
        src_vid = f'[{next_src_vid}]'
    stitch_cmd.append('-filter_complex')
    stitch_cmd.append(filter_complex)
    stitch_cmd.append('-map')
    stitch_cmd.append(f'{src_vid}')
    stitch_cmd.append('-movflags')
    stitch_cmd.append('+faststart')
    stitch_cmd.append('-y')
    stitch_cmd.append(seg_interleaved)
    pprint(stitch_cmd)
    add_proc(stitch_cmd)

    # Add corrected audio to interleaved slide video
    add_proc(['ffmpeg',
              '-i', seg_interleaved,
              '-i', seg_corrected_a,
              '-map', '0:v:0',
              '-map', '1:a:0',
              '-y', seg_talk_av
    ])

talk2 = [ 2,
     '../../obs/track-ordered/hardware/02_Jigita_jump_to_soldering.png',
         '00:05:16', '00:05:27', '00:34:10', '00:35:29'
]
talk3 = ( 3,
     '../../obs/track-ordered/hardware/03_VoltQuest_Open_Source_Hardware_Gaming.png',
     '00:35:44', '00:37:35', '00:52:24'
)
talk4 = ( 4,
     '../../obs/track-ordered/hardware/04_Homelabbing_with_bare_metal.png',
     '00:58:24', '01:00:00', '01:00:30', '01:02:20',
     '01:04:00', '01:04:29', '01:04:50', '01:05:23',
     '01:06:35', '01:14:10', '01:15:30', '01:16:00',
     '01:17:00', '01:19:30', '01:23:40', '01:26:38',
     '01:27:20', '01:29:13', '1:36:45'
)
talk5 = ( 5,
     '../../obs/track-ordered/hardware/05_CoryDora_A_Macropad_A_Supply.png',
         '01:40:00', '01:40:42', '02:09:13', '02:09:37'
)
talk6 = ( 6,
     '../../obs/track-ordered/hardware/06_Makerville_Badge.png',
         '02:11:50', '02:12:00', '02:37:22', '02:37:36'
)
talk7 = ( 7,
     '../../obs/track-ordered/hardware/07_Because_Glancing_at_Your_Phone.png',
         '02:38:40', '02:39:06', '02:55:00','02:57:05'
)

master_video(talk2)
master_video(talk3)
master_video(talk4)
master_video(talk5)
master_video(talk6)
master_video(talk7)
