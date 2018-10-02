import os
import download_script

TEST_DIR = "test_files"

afiles = sorted([os.path.join(TEST_DIR, afi) for afi in os.listdir(TEST_DIR)
                 if ".wav" in afi])

download_script.try_autocut(afiles, "test_output.mp3", merge_segments=True)
