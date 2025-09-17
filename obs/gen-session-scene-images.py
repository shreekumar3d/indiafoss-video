#!/usr/bin/env python3
#
# Generate scene images for a devroom/main track day long session
#
# ./gen-session-scene-images.py --track day1-audi1
# ./gen-session-scene-images.py --devroom aosp
#
# Devrooms have list of session titles.
# Tracks are exported from website schedule page
#
import csv
import cairo
from pprint import pprint
import subprocess
from xml.sax.saxutils import escape
from pathlib import Path
import os
import string
import argparse
from datetime import datetime
import tempfile

def get_text_width_mm(text, family='Inter', size=28, dpi=78):
    # Off-screen SVG surface
    surface = cairo.SVGSurface(None, 1, 1) # size does not matter
    ctx = cairo.Context(surface)
    ctx.select_font_face(family, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    xbearing, ybearing, width, height, xadvance, yadvance = ctx.text_extents(text)
    # Pixel to mm conversion
    width_mm = width * 25.4 / dpi
    return width_mm

def span_text(text, size, limit):
    words = text.split(' ')
    lines = []
    this_line = []
    for word in words:
        test_line = ' '.join(this_line+[word])
        tw = get_text_width_mm(test_line, size=size)
        if tw > limit:
            partial_line = ' '.join(this_line)
            lines.append(partial_line)
            this_line = []
        this_line.append(word)
    if len(this_line)>0:
        lines.append(' '.join(this_line))
    return lines

def gen_speaker_plus_slides(talk_info, track2dir, output_base_dir, file_prefix):

    template_image_dir = "templates/images/"
    title = talk_info['title'].strip()

    title_line = span_text(title, 28, 460) # limit from template
    if len(title_line)>2:
        raise ValueError("Too long title:", title)

    title_only = ""
    title_line1 = ""
    title_line2 = ""

    track = talk_info['track']
    if len(title_line)==1:
        title_only = title_line[0]
        title_line1 = ""
        title_line2 = ""
    else:
        title_line1 = title_line[0]
        title_line2 = title_line[1]

    speaker_info = talk_info['speakers'][0]
    speaker1 = speaker_info['name']
    speaker1_designation = speaker_info['designation']
    speaker1_company = speaker_info['company']

    speaker2 = ""
    speaker2_designation = ""
    speaker2_affiliation = ""
    if len(talk_info['speakers'])>1:
        speaker_info = talk_info['speakers'][1]
        speaker2 = speaker_info['name']
        if len(speaker_info['company'])>0:
            speaker2_designation = speaker_info['company']
        else:
            speaker2_designation = speaker_info['designation']
        if len(speaker1_company)>0:
            speaker1_designation = speaker1_company
            speaker1_company = ""

    company_line = span_text(speaker1_company, 24, 120) # limit from template
    if len(company_line)>2:
        raise ValueError("Company name too long:", speaker1_company)
    else:
        speaker1_company1 = company_line[0]
        speaker1_company2 = ""
        if len(company_line)>1:
            speaker1_company2 = company_line[1]
        #print(speaker1_company1)
        #print(speaker1_company2)
    template = open("templates/talk-presentation-section.svg","r").read()
    template = template.replace('$TITLE-LINE1$', escape(title_line1))
    template = template.replace('$TITLE-LINE2$', escape(title_line2))
    template = template.replace('$TITLE-ONLY$', escape(title_only))
    template = template.replace('$SPEAKER1$', escape(speaker1))
    template = template.replace('$SPEAKER1-DESIGNATION$', escape(speaker1_designation))
    template = template.replace('$SPEAKER1-COMPANY1$', escape(speaker1_company1))
    template = template.replace('$SPEAKER1-COMPANY2$', escape(speaker1_company2))
    template = template.replace('$SPEAKER2$', escape(speaker2))
    template = template.replace('$SPEAKER2-DESIGNATION$', escape(speaker2_designation))
    template = template.replace('$TEMPLATE-IMAGE-DIR$', template_image_dir, -1)

    temp_svg = tempfile.NamedTemporaryFile(mode='w', delete=True)
    temp_svg.write(template)
    temp_svg.flush()

    track_dir = track2dir[track] if type(track2dir) is dict else track2dir
    track_dir = Path(os.path.join(output_base_dir, track_dir))
    track_dir.mkdir(parents=True, exist_ok=True)
    output_file = '_'.join(title.split(' ')[:5])
    output_file += '.png'
    output_file = output_file.replace(':','',-1) # remove troublesome chars in filename
    output_file = output_file.replace('`','',-1)
    output_file = output_file.replace('-','',-1)
    output_file = output_file.replace(',','',-1)
    output_file = output_file.replace('+','',-1)
    output_file = output_file.replace('@','',-1)
    output_file = output_file.replace('__','_',-1)
    output_file = os.path.join(track_dir, file_prefix+output_file)
    cmd = ['inkscape', '--export-type=png', '--export-width=1920',
           '--export-height=1080', '--export-filename', output_file, temp_svg.name]
    print(output_file)
    subprocess.run(cmd, check=True)
    # ensure the file actually got created
    open(output_file,'r')

def get_track_talks(filename):
    track_sessions = []
    with open(filename, 'r') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader) # skip header
        for row in reader:
            # skip breaks, begin, end sessions etc
            if len(row[7]) == 0: # no speakers
                continue
            # 2 => time, 0 => title
            talk_time = datetime.strptime(row[2], "%H:%M").time()
            track_sessions.append((talk_time, row[0]))
    track_sessions.sort()
    return map(lambda x: x[1], track_sessions)

# Load all talk metadata. This file may nee manual changes for formatting,
# inconsistent information provided by speakers, abbreviations, etc
talks = []
talk_info = {}

with open('indiafoss-cfp-track.csv','r') as csvfile:
    reader = csv.reader(csvfile)
    header = next(reader) # skip header
    for row in reader:
        if len(row[1])>0:
            if talk_info:
                talks.append(talk_info)
                talk_info = {}
            talk_info['type'] = row[0]
            talk_info['track'] = row[8]
            talk_info['title'] = row[1]
            talk_info['duration'] = row[3]
            speaker_info = {
                "name" : row[5],
                "designation" : row[6],
                "company" : row[7]
            }
            talk_info['speakers'] = [ speaker_info ]
        elif len(row[5])>0:
            speaker_info = {
                "name" : row[5],
                "designation" : row[6],
                "company" : row[7]
            }
            talk_info['speakers'].append(speaker_info)
        else:
            if talk_info:
                talks.append(talk_info)
                talk_info = {}
# Handle unprocessed bits
if talk_info:
    talks.append(talk_info)
    talk_info = {}

#print(f'Number of sessions = {len(talks)}')

# It's a short list, so feed in by hand
track2dir = {
    'Main track' : 'main',
    'Main Track' : 'main',
    'Geopolitics and Policy in FOSS Devroom' : 'policy',
    'Open Hardware Devroom' : 'hardware',
    'Android Open Source Project (AOSP) Devroom' : 'aosp',
    'Compilers, Programming Languages and Systems Devroom' : 'compilers',
    'Open Data Devroom' : 'data',
    'FOSS in Science Devroom' : 'science'
}

def gen_obs_track_images(track_talks, output_track):
    missing_talks = []
    output_base_dir = 'track-ordered'
    for index, talk_title in enumerate(track_talks):
        talk_title = talk_title.strip() # extra whitespace
        matching_talk = [item for item in talks if item["title"]==talk_title]

        if talk_title.startswith('-'):
            print(f'Skipping devroom manager-led section : {talk_title}')
            continue
        elif talk_title.startswith('.'):
            print(f'Skipping special instruction : {talk_title}')
            continue
        elif len(matching_talk) == 0:
            # Schedule is entered by hand, so perhaps we're only fed a prefix
            matching_talk = [item for item in talks if item["title"].startswith(talk_title[:len(talk_title)//2])]
            if len(matching_talk) == 1:
                print(f'Resolving "{talk_title}" with partial match!')
            else:
                print(f'Missing talk "{talk_title}"')
                missing_talks.append(talk_title)
        elif len(matching_talk) != 1:
            raise ValueError(f"Bad metadata - multiple matches for {talk_title}")

        if len(matching_talk) == 1:
            gen_speaker_plus_slides(matching_talk[0], output_track, output_base_dir, '%02d_'%(index+1))
    if len(missing_talks)>0:
        raise ValueError(f"Missing talks {missing_talks}")

def gen_obs_track_images_from_schedule(output_track):
    track_talks = get_track_talks(f'track-lists/{output_track}.csv')
    gen_obs_track_images(track_talks, output_track)

def gen_obs_track_images_for_devroom(output_track):
    track_talks = [ x.strip() for x in open(f'track-lists/{output_track}.txt','r').readlines() ]
    gen_obs_track_images(track_talks, output_track)

parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--track")
group.add_argument("--devroom")
args = parser.parse_args()

if args.devroom:
    gen_obs_track_images_for_devroom(args.devroom)
if args.track:
    gen_obs_track_images_from_schedule(args.track)

#gen_obs_track_images_for_devroom('aosp')
#gen_obs_track_images_from_schedule('day2-audi2')
#gen_obs_track_images_from_schedule('day2-audi2')
#gen_obs_track_images_from_schedule('day1-audi1')
#gen_obs_track_images_from_schedule('day1-audi2')
#gen_obs_track_images_from_schedule('day2-audi1')
#gen_speaker_plus_slides(talks[0])
