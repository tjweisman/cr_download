import os
import download_script

vdir = "/tmp/tmpI5WDyE"

vfiles = sorted([vfi for vfi in os.listdir(vdir) if ".wav" in vfi])


#download_script.try_autocut()

download_script.autocut_files(vdir, vfiles, "output_cut_part*.mp3",
                              debug = True, merge_segments=False)
