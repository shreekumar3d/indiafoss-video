import audalign as ad
from pprint import pprint

correlation_rec = ad.CorrelationRecognizer()

# Cut a sufficiently long audio track from both videos you wish to align
# In this case, we take a 10 minute segment
#
# ffmpeg -i localrec-oh.mkv -to 05:00 -vn -acodec pcm_s16le cut-localrec-oh.wav
# ffmpeg -i procam-oh.mp4 -to 10:00 -vn -acodec pcm_s16le cut-procam-oh.wav

# Now, align them
results = ad.align_files("cut-procam-oh.wav", "cut-localrec-oh.wav", recognizer = correlation_rec)
pprint(results)

# align will report an alignment difference in seconds

#cor_spec_rec = ad.CorrelationSpectrogramRecognizer()
# results can then be sent to fine_align
#fine_results = ad.fine_align(
#    results,
#    recognizer=cor_spec_rec,
#)
#pprint(fine_results)
