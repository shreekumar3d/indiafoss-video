#
# Generate scene images for all sessions
#
#
import csv
import cairo
from pprint import pprint
import subprocess
from xml.sax.saxutils import escape
from pathlib import Path
import os
import string

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

def gen_speaker_plus_slides(talk_info):
    tid = "talk1"
    session_track = "main"
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

    f = open("out.svg", "w")
    f.write(template)
    f.close()

    track_dir = Path(track)
    track_dir.mkdir(parents=True, exist_ok=True)
    #output_file = os.path.join(track_dir,'_'.join(title.split(' ')[:4]))+'.png'
    output_file = ('_'.join(title.split(' ')[:4]))+'.png'
    output_file = output_file.replace(':','',-1) # remove troublesome chars in filename
    cmd = ['inkscape', '--export-type=png', '--export-width=1920',
           '--export-height=1080', '--export-filename', output_file, 'out.svg']
    print(output_file)
    subprocess.run(cmd, check=True)
    # ensure the file actually got created
    open(output_file,'r')

# Load all talk metadata
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

print(f'Number of sessions = {len(talks)}')

# Generate scene images
for talk_info in talks:
    gen_speaker_plus_slides(talk_info)
#gen_speaker_plus_slides(talks[0])
