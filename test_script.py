import os, re
import download_script
import pickle
import tempfile

import cr_download.autocutter as autocutter

TEST_DIR = "test"
TEST_WAVS = "wav_files"
TEST_AUTOCUTTER_OUTPUT = "test_output*.mp3"

afiles = sorted([os.path.join(TEST_DIR, TEST_WAVS, afi)
                 for afi in os.listdir(os.path.join(TEST_DIR, TEST_WAVS))])

def test_autocut():
    autocutter.autocut(afiles,
                       os.path.join(TEST_DIR, TEST_AUTOCUTTER_OUTPUT),
                       debug=True,
                       merge_segments=True)

#pcm_transitions = [(77434405, 395484195), (446232167, 717033845)]

#tdir = tempfile.mkdtemp()
#autocutter.recut_files(afiles, tdir, pcm_transitions, "test_output_part*.mp3",
#                       merge=False)
#autocutter.autocut(afiles, "test_output.mp3", merge_segments=True,
#        fingerprint_data = fingerprint_data)
#get_autocut_errors([os.path.join(TEST_DIR, "overture_wav.wav")])
