"""fingerprint_sequence.py: handle fingerprint data for a set of audio
files

"""

import os
import hashlib
import pickle

from progressbar import progressbar

from .. import appdata
from . import fingerprint_utils

class FingerprintException(Exception):
    pass

class FingerprintSequence:
    """class to store fingerprint data for a set of audio files.

    """
    def __init__(self, audio_files=None):
        self._sequence = []
        self.samplerate = None
        self.channels = None
        self.duration = 0.0

        if audio_files is not None:
            self.load_from_audio_files(audio_files)

    def load_from_audio_files(self, audio_files):
        """load the FingerprintSequence from a sequence of audio files.
        """
        for filename in progressbar(audio_files):
            fingerprint, data = fingerprint_utils.fingerprint_full_file(filename)
            self.duration += data["duration"]
            if ((self.channels is not None and
                 data["channels"] != self.channels) or
                (self.samplerate is not None and
                 data["samplerate"] != self.samplerate)):
                raise FingerprintException(
                    """Fingerprint sequencer doesn't know how to handle input
                    files with different channelno or sample rate!"""
                )
            else:
                self.channels = data["channels"]
                self.samplerate = data["samplerate"]

            self._sequence += fingerprint

        self.fingerprint_rate = len(self._sequence) / self.duration

    def window_size(self, window_time):
        """get the number of fingerprint frames for a given duration (in
        seconds)

        """
        return int(window_time * self.fingerprint_rate)

    def windows(self, window_size=None, window_time=None):
        """cut up the fingerprint sequence into a list of windows, each of a
        fixed size"""
        if window_size is None and window_time is not None:
            window_size = self.window_size(window_time)

        if window_size is None:
            raise FingerprintException(
                "You must provide either a window size or a window duration"
            )

        return [self._sequence[i:i+window_size]
                for i in range(0, len(self._sequence), window_size)]

    def index_to_pcm(self, index):
        """convert the index of a fingerprint to a pcm index
        """
        return int(self.samplerate * index / self.fingerprint_rate)

    def index_to_timestamp(self, index):
        """convert the index of a fingerprint to a timestamp (in seconds)

        """
        return int(index / self.fingerprint_rate)

def _get_cache_filename(audio_files):
    basenames = [os.path.basename(afile) for afile in audio_files]
    return hashlib.md5("".join(basenames).encode("utf-8")).hexdigest()

def _load_cached_fingerprints(filename):
    fprints = None

    try:
        with appdata.open_cache_file(filename, "rb") as pfi:
            fprints = pickle.load(pfi)
            print("Loaded fingerprints from {}.".format(
                appdata.cache_filename(filename)))
    except(IOError, pickle.UnpicklingError, FileNotFoundError):
        print("Could not open fingerprints from {}.".format(
            appdata.cache_filename(filename)))

    return fprints

def load_fingerprints(audio_files, use_cache=False):
    """load a fingerprint sequence from an array of audio files.

    if use_cache is specified, try to load the sequence from a pickle
    in the cache directory first.

    """
    fingerprints = None
    if use_cache:
        cache_file = _get_cache_filename(audio_files)
        fingerprints = _load_cached_fingerprints(cache_file)

    if fingerprints is None:
        fingerprints = FingerprintSequence(audio_files)

    if use_cache:
        with appdata.open_cache_file(cache_file, "wb") as pfi:
            pickle.dump(fingerprints, pfi)

    return fingerprints
