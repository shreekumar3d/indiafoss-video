import audalign as ad
from pprint import pprint

correlation_rec = ad.CorrelationRecognizer()

# Cut a sufficiently long audio track from both videos you wish to align
# In this case, we take a 10 minute segment
#
#ffmpeg -i localrec-1.mkv -to 05:00 -vn -acodec pcm_s16le cut-localrec-1.wav
#ffmpeg -i procam-1.mp4 -to 05:00 -vn -acodec pcm_s16le cut-procam-1.wav

# Now, align them
results = ad.align_files("cut-procam-1.wav", "cut-localrec-1.wav", recognizer = correlation_rec)
pprint(results)

# align will report an alignment difference in seconds

#cor_spec_rec = ad.CorrelationSpectrogramRecognizer()
# results can then be sent to fine_align
#fine_results = ad.fine_align(
#    results,
#    recognizer=cor_spec_rec,
#)
#pprint(fine_results)
