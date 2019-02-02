from __future__ import print_function

import os
from itertools import chain
import pickle
import tempfile
import shutil

from .. import media_utils
from .. import configuration
from .. import appdata
from . import fingerprint_utils

MASK = 0xFF000000

class SampleFingerprint:
    """class to store fingerprint data for one of the Critical Role
    transition soundtracks

    """
    def __init__(self, fingerprint, mask=MASK):
        self.fingerprint = fingerprint
        self.mask = mask
        masked_prints = [fprint & mask for fprint in fingerprint]
        self.masked_prints_i = fingerprint_utils.invert(masked_prints)
        self.masked_prints_s = set(masked_prints)

    def __len__(self):
        return len(self.fingerprint)

    def window_error(self, window_print, check_high_bits=True):
        """find minimum pct bit error for a short fingerprint segment compared
        to the fingerprint of a transition soundtrack.

        we slide the window across the sample, computing percent bit
        errors, and take the minimum. If CHECK_HIGH_BITS is specified,
        do a first pass so we only check points where the high-order
        bits of the sample/window agree.
        """
        offsets = range(len(self) - len(window_print))

        if check_high_bits:
            masked_prints = {prt & self.mask for prt in window_print}
            intersect = masked_prints & self.masked_prints_s
            offsets = chain(*[self.masked_prints_i[val]
                              for val in intersect])

        errs = [
            fingerprint_utils.total_error(
                window_print, self.fingerprint[offset:])
            for offset in offsets
        ]

        if not errs:
            return 1.0

        return min(errs)

def load_prints(mask=MASK, sample_file=None):
    """Load transition soundtrack fingerprint data from file(s).

    If SAMPLE_FILE is specified, this function tries to load
    fingerprint data from a pickle file stored in the cache directory.

    If that fails, it will load the actual .mp3 files for transition
    soundtracks from application resources, regenerate the fingerprint
    data, and save it to the specified pickle file.

    If no SAMPLE_FILE is specified, just generate the fingerprint
    data.

    """

    print("Loading sample fingerprint data...")
    if sample_file is not None:
        try:
            pickle_path = appdata.cache_filename(sample_file)
            with appdata.open_cache_file(sample_file, "rb") as pfi:
                prints = pickle.load(pfi)
            return prints
        except(IOError, pickle.UnpicklingError, FileNotFoundError):
            print("Could not open samples from {}. ".format(pickle_path))

    print("Generating fingerprints...")
    prints = {}

    tmpdir = tempfile.mkdtemp()
    sample_audio_files = configuration.data["sample_audio_files"]
    for key, filename in sample_audio_files.items():
        wav_file = os.path.join(tmpdir,
                                media_utils.change_ext(filename, ".wav"))

        #not an error: resource management API uses /, not system pathsep
        mp3_file = appdata.resource_filename(
            appdata.SOUND_DIR + "/" + filename)

        media_utils.ffmpeg_convert(mp3_file, wav_file)
        fingerprints, _ = fingerprint_utils.fingerprint_full_file(wav_file)
        prints[key] = SampleFingerprint(fingerprints, mask)

    shutil.rmtree(tmpdir)

    if sample_file is not None:
        print(("Writing fingerprints to {}...".format(pickle_path)))
        with appdata.open_cache_file(sample_file, "wb") as pfi:
            pickle.dump(prints, pfi)

    return prints
