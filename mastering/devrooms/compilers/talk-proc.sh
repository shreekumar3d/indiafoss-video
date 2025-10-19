AFIX=afix-$1

# Replicate audio channel L to R, overlay fullscreen art, encode video
ffmpeg -i $1 -i ../overlay-video-full-screen.png -filter_complex "[0:v][1:v]overlay=0:0" -af "pan=stereo|FL=FL|FR=FL" -y $AFIX

# Characterize audio levels
ffmpeg -i $AFIX -filter:a loudnorm=print_format=json -f null /dev/null 2>&1 >/dev/null | sed -n '/{/,/}/p' > /tmp/info

# Extract parameters
ii=`grep \"input_i\" /tmp/info | cut -d: -f2 | tr -cd [:digit:].-`
itp=`grep \"input_tp\" /tmp/info | cut -d: -f2 | tr -cd [:digit:].-`
ilra=`grep \"input_lra\" /tmp/info | cut -d: -f2 | tr -cd [:digit:].-`
it=`grep \"input_thresh\" /tmp/info | cut -d: -f2 | tr -cd [:digit:].-`
to=`grep \"target_offset\" /tmp/info | cut -d: -f2 | tr -cd [:digit:].-`

# Apply audio correction
ffmpeg -i $AFIX -c:v copy -af loudnorm=linear=true:I=-16:LRA=11:tp=-1.5:measured_I=$ii:measured_LRA=$ilra:measured_tp=$itp:measured_thresh=$it:offset=$to:print_format=summary -y final-$1
