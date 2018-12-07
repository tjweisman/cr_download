import os
import pickle
import tempfile
import shutil

import media_utils
import cr_settings
import autocutter_utils

MASK = 0xFF000000

class SampleFingerprint:
    """class to store fingerprint data for one of the Critical Role
    transition soundtracks

    """
    def __init__(self, fingerprint, mask = MASK):
        self.fingerprint = fingerprint
        self.mask = mask
        masked_prints = [fprint & mask for fprint in fingerprint]
        self.masked_prints_i = autocutter_utils.invert(masked_prints)
        self.masked_prints_s = set(masked_prints)

    def __len__(self):
        return len(self.fingerprint)


def load_prints(mask = MASK, sample_file = None):
    """Load transition soundtrack fingerprint data from file(s).

    If SAMPLE_FILE is specified, this function tries to load
    fingerprint data from a pickle file stored in the config
    directory.

    If that fails, it will load the actual .mp3 files for transition
    soundtracks from the config directory, regenerate the fingerprint
    data, and save it to the specified pickle file.

    If no SAMPLE_FILE is specified, just generate the fingerprint
    data.

    """
    
    print("Loading sample fingerprint data...")
    if sample_file is not None:
        pickle_path = os.path.join(cr_settings.CONFIG_DIR, sample_file)
        try:
            with open(pickle_path, "r") as pfi:
                prints = pickle.load(pfi)
            return prints
        except IOError:
            print("Could not open samples from {}. ".format(pickle_path))

    print("Generating fingerprints...")
    prints = {}
    sample_dir = os.path.join(cr_settings.CONFIG_DIR, "break_sounds")

    tmpdir = tempfile.mkdtemp()
    sample_audio_files = cr_settings.DATA["sample_audio_files"]
    for key, filename in sample_audio_files.iteritems():
        wav_file = os.path.join(tmpdir,
                                media_utils.change_ext(filename, ".wav"))
        media_utils.mp4_to_audio_file(
            os.path.join(sample_dir, filename), wav_file
        )
        fingerprints, _ = autocutter_utils.fingerprint_full_file(wav_file)
        prints[key] = SampleFingerprint(fingerprints, mask)

    shutil.rmtree(tmpdir)

    if sample_file != None:
        print("Writing fingerprints to {}...".format(pickle_path))
        with open(pickle_path, "w") as pfi:
            pickle.dump(prints, pfi)

    return prints
