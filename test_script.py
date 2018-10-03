import os, re
import download_script
import pickle
import tempfile

import cr_download.autocutter as autocutter

TEST_DIR = "test_files"

afiles = sorted([os.path.join(TEST_DIR, afi) for afi in os.listdir(TEST_DIR)
                 if re.match(r"crvid.*\.wav", afi)])

with open(os.path.join(TEST_DIR, "test_fprint_data")) as pfi:
    fingerprint_data = pickle.load(pfi)

pcm_transitions = [(77434405, 395484195), (446232167, 717033845)]

tdir = tempfile.mkdtemp()
autocutter.recut_files(afiles, tdir, pcm_transitions, "test_output_part*.mp3",
                       merge=False)
#autocutter.autocut(afiles, "test_output.mp3", merge_segments=True,
#        fingerprint_data = fingerprint_data)
#get_autocut_errors([os.path.join(TEST_DIR, "overture_wav.wav")])
