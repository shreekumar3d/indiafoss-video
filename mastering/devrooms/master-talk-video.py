#!/usr/bin/env python3
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
import argparse
from enum import Enum

from enum import Enum

class Pipeline(Enum):
    full = "full"
    clips = "clips"
    audio = "audio"

    def __str__(self):
        # This makes the help message and error messages more user-friendly
        return self.value

def add_proc(message, cmd, capture_output=False, verbose=False):
    global skip_proc
    print(message)
    if capture_output:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result
    else:
        if verbose:
            subprocess.run(cmd, check=True)
        else:
            subprocess.run(cmd, capture_output=True, text=True, check=True)

def master_video(cfg, this_talk, pipeline, verbose=False):
    devroom = cfg['devroom']
    noise_profile_file = cfg["noise-profile"]
    noise_profile = f'{devroom}/{noise_profile_file}'
    # global audio filter
    extra_audio_filters = ','+cfg['audio_filter'] if 'audio_filter' in cfg else ''

    livestream = cfg['livestream']
    procam = cfg['vcam']
    vid_slides = f'{devroom}/{livestream}'
    vid_procam = f'{devroom}/{procam}'
    nr_factor = cfg['proc']['noise-reduction']
    offset = cfg['proc']['vcam-offset']
    procam_offset = timedelta(seconds=abs(offset))

    # override audio filters - may need to do per speaker at some time point in time
    extra_audio_filters = ','+this_talk['audio_filter'] if 'audio_filter' in this_talk else extra_audio_filters

    talk_idx = this_talk['index']
    info_image = this_talk['info-image']
    fullscreen_template = this_talk['fullscreen-template']

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

    video_cuts = this_talk['cuts']
    start_sv = datetime.strptime(video_cuts[0], '%H:%M:%S')
    end_sv = datetime.strptime(video_cuts[-1], '%H:%M:%S')

    seg_duration = datetime.min + (end_sv-start_sv)
    seg_duration = seg_duration.strftime('%H:%M:%S.%f')[:-3]
    if offset < 0:
        start_procam = start_sv - procam_offset
    else:
        start_procam = start_sv + procam_offset

    t_start_sv = start_sv.strftime('%H:%M:%S.%f')[:-3]
    t_start_procam = start_procam.strftime('%H:%M:%S.%f')[:-3]
    print('Talk ', talk_idx)
    print(f'  Video Offset : {cfg["proc"]["vcam-offset"]}')
    print(f'  Start : sv @ {t_start_sv} procam @ {t_start_procam}')
    print(f'  Length: {seg_duration}')
    print(f'  Noise Reduction : {nr_factor}')
    print(f'  Audio Filters : {extra_audio_filters[1:]}')

    overlap = cfg["proc"]["overlap"] # in seconds between clips
    is_first_seg = True
    is_fs_video = True
    seg_idx = 0
    clips = []
    for start_pos, end_pos in zip(video_cuts, video_cuts[1:]):
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

    if pipeline == Pipeline.full:
        # Cut out a segment (of interest) of the two source videos
        # no audio needed from livestream
        add_proc('Cutting livestream...',
                 ['ffmpeg',
                  '-i', vid_slides,
                  '-ss', t_start_sv, '-t', seg_duration,
                  '-an', '-c:v', 'copy',
                  '-y', seg_vid_slides
                 ],
                 verbose = verbose
        )
        add_proc('Cutting camera video...',
                 ['ffmpeg',
                  '-i', vid_procam,
                  '-ss', t_start_procam, '-t', seg_duration,
                  '-c', 'copy', 
                  '-y', seg_procam_av
                 ],
                 verbose = verbose
        )

        # Cut out the segment - combined with the fullscreen template
        add_proc('Generating fullscreen video...',
                 ['ffmpeg', '-i', seg_procam_av, '-i', fullscreen_template, '-an',
                  '-filter_complex',
                  '[0:v][1:v]overlay=0:0',
                  '-y', seg_speaker_only
                 ],
                 verbose = verbose
        )

    # Create a video that stuffs
    #  - procam video
    #  - slides
    #  - OBS template with speaker info
    # into one video
    #
    slides_cw, slides_ch = cfg['proc']['slides']['crop']['wh']
    slides_cx, slides_cy = cfg['proc']['slides']['crop']['xy']
    slides_sx, slides_sy = cfg['proc']['slides']['scale']
    slides_px, slides_py = cfg['proc']['slides']['position']
    video_cw, video_ch = cfg['proc']['video']['crop']['wh']
    video_cx, video_cy = cfg['proc']['video']['crop']['xy']
    video_sx, video_sy = cfg['proc']['video']['scale']
    video_px, video_py = cfg['proc']['video']['position']
    slides=f'[1:v]crop={slides_cw}:{slides_ch}:{slides_cx}:{slides_cy},scale={slides_sx}:{slides_sy}[v1];'
    video=f'[2:v]crop={video_cw}:{video_ch}:{video_cx}:{video_cy},scale={video_sx}:{video_sy}[v2];'
    mix_slides=f'[0:v][v1]overlay={slides_px}:{slides_py}[mix1];'
    mix_video=f'[mix1][v2]overlay={video_px}:{video_py}[outv]'
    if pipeline == Pipeline.full:
        add_proc('Regenerating slides+camera video...',
                 ['ffmpeg', '-i', info_image, '-i', seg_vid_slides, '-i', seg_procam_av,
                  '-filter_complex',
                  slides +
                  video +
                  mix_slides +
                  mix_video,
                  '-map', '[outv]',
                  '-y', seg_vid_slides_realign
                 ],
                 verbose = verbose
        )

    if pipeline == Pipeline.full:
        # Extract only the audio
        add_proc('Extracting audio track...',
                 ['ffmpeg',
                  '-i', seg_procam_av,
                  '-vn',
                  '-acodec', 'pcm_s16le',
                  '-y', seg_procam_a
                 ],
                 verbose = verbose
        )

    result = None
    if pipeline in [Pipeline.audio, Pipeline.full]:
        # Denoise audio using existing profile
        add_proc('Denoising audio track...',
                 ['sox',
                  '--multi-threaded',
                  seg_procam_a, seg_procam_nn_a,
                  'noisered', noise_profile,
                  str(nr_factor)
                 ],
                 verbose = verbose
        )
        # camera audio is mono - replicate in both L/R for better
        # volume
        add_proc('Replicating R=L in audio track...',
                 ['ffmpeg',
                  '-i', seg_procam_nn_a,
                  '-af', f'pan=stereo|FL=FL|FR=FL{extra_audio_filters}',
                  '-acodec', 'pcm_s16le',
                  '-y', seg_filtered_a
                 ],
                 verbose = verbose
        )
        # Measure audio characteristics using loudnorm
        result = add_proc('Measuring loudness of audio track...',
                          ['ffmpeg',
                           '-i', seg_filtered_a,
                           '-filter:a', 'loudnorm=print_format=json',
                           '-f', 'null', '/dev/null'
                          ],
                          capture_output = True,
                          verbose = verbose
                         )

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
        add_proc('Normalizing audio volume...',
                 ['ffmpeg',
                  '-i', seg_filtered_a,
                  '-af',
                  f'loudnorm={loudnorm}',
                  '-ar', '48000', # loudnorm upsamples to 96kHz+
                  '-y', seg_corrected_a
                 ],
                 verbose=verbose
        )

    if pipeline in [Pipeline.clips, Pipeline.full]:
        # Generate all the cuts of the video files
        for seg_idx, src_vfile, start, duration, out_vfile in clips:
            add_proc(f'Generating segment {seg_idx} start={str(start)} duration={duration}',
                     ['ffmpeg',
                      '-i', src_vfile,
                      '-ss', str(start), '-t', duration,
                      '-an',
                      '-y', out_vfile
                     ],
                     verbose=verbose
            )

    if pipeline in [Pipeline.clips, Pipeline.full]:
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
        if verbose:
            pprint(stitch_cmd)
        add_proc('Merging video segments with crossfades...',
                 stitch_cmd,
                 verbose=verbose)

    # Add corrected audio to interleaved slide video
    add_proc('Merging corrected audio into video to generate FINAL VIDEO...',
             ['ffmpeg',
              '-i', seg_interleaved,
              '-i', seg_corrected_a,
              '-c:v', 'copy',
              '-map', '0:v:0',
              '-map', '1:a:0',
              '-y', seg_talk_av
             ],
             verbose=verbose
    )
    print('DONE!')
    print(f'Output generated : {seg_talk_av}')

parser = argparse.ArgumentParser()
parser.add_argument("devroom_json", help="""
    Devroom configuration file (json).
""")
parser.add_argument('--verbose', '-v', action='store_true', default=False, help="""
    Enable verbose messages, showing ffmpeg execution, progress, warnings, etc.
""")
parser.add_argument('--index', '-i', type=int, help="""
    Generate video only for talk having this index in the json file. If not
    specified, all talk videos are processed.
""")
parser.add_argument('--pipeline', '-p', type=Pipeline, choices=list(Pipeline),
    help="""Run a part of the processing pipeline.""")
args = parser.parse_args()

if args.pipeline is None:
    args.pipeline = Pipeline(Pipeline.full)

cfg = json.loads(open(args.devroom_json,'r').read())

if args.index:
    for talk in cfg['talks']:
        if args.index == talk['index']:
            master_video(cfg, talk, args.pipeline, args.verbose)
else:
    for talk in cfg['talks']:
        master_video(cfg, talk, args.pipeline, args.verbose)
