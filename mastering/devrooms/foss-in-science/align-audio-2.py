import audalign as ad
from pprint import pprint

correlation_rec = ad.CorrelationRecognizer()

# Cut a sufficiently long audio track from both videos you wish to align
# In this case, we take a 10 minute segment

# rip the entire video as we're looking at somewhere halfway... lazy me!
#ffmpeg -i ytlive.mp4 -vn -acodec pcm_s16le -y cut-ytlive-2.wav
#ffmpeg -i procam-2.mp4 -to 20:00 -vn -acodec pcm_s16le -y cut-procam-2.wav

# Now, align them
results = ad.align_files("cut-procam-2.wav", "cut-ytlive-2.wav", recognizer = correlation_rec)
pprint(results)

# align will report an alignment difference in seconds

#cor_spec_rec = ad.CorrelationSpectrogramRecognizer()
# results can then be sent to fine_align
#fine_results = ad.fine_align(
#    results,
#    recognizer=cor_spec_rec,
#)
#pprint(fine_results)
