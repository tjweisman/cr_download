import os
import download_script

vdir = "/tmp/tmpdriSrt"
vfiles = sorted([vfi for vfi in os.listdir(vdir) if ".wav" in vfi])

download_script.autocut_files(vdir, vfiles, "output_cut.mp3")
