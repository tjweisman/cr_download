"""fingerprint_sequence.py

handle fingerprint data for a set of audio files
"""

from tqdm import tqdm

import autocutter_utils

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
        for filename in tqdm(audio_files):
            fingerprint, data = autocutter_utils.fingerprint_full_file(filename)
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
