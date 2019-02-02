"""wav_sequence: module providing tools to open a sequence of .wav
files as if it were a single audio file

"""

from collections import deque
import wave

BUFFER_SIZE = 1024

class WavSequence:
    """class to treat a sequence of wav files as a single audio file
    """
    def __init__(self, filenames):
        self._filenames = deque(filenames)
        self._current_file = None
        self.frame_index = 0

    def open(self):
        """open the first wav file in the sequence
        """
        if self._filenames:
            self._current_file = wave.open(self._filenames.popleft(), "rb")

    def close(self):
        """close the current (only) open file in the sequence
        """
        self._current_file.close()

    def readframes(self, num_frames):
        """read at most num_frames frames from the file sequence
        """
        frames = self._current_file.readframes(num_frames)
        if len(frames) < num_frames and self._filenames:
            self._current_file.close()
            self._current_file = wave.open(self._filenames.popleft(), "rb")
            frames += self.readframes(num_frames - len(frames))

        return frames

    def _advance_frames(self, num_frames, output_file=None):
        frames_left = num_frames
        frames = [0]
        while frames:
            if num_frames == -1:
                to_read = BUFFER_SIZE
            else:
                to_read = min(BUFFER_SIZE, frames_left)

            frames = self.readframes(to_read)
            if output_file is not None:
                output_file.writeframes(frames)
            frames_left -= to_read

    def skip_frames(self, num_frames):
        """skip ahead num_frames frames in the file sequence (or to end of file),
        using a buffer

        """
        self._advance_frames(num_frames)

    def copy_frames(self, num_frames, output_file):
        """copy at most num_frames frames from the file sequence to
        output_file, using a buffer

        """
        self._advance_frames(num_frames, output_file)

    def copy_to_end(self, output_file):
        """copy the rest of the sequence to output_file"""

        self._advance_frames(-1, output_file)


    def getparams(self):
        """get wav file metadata for the currently open file
        """
        return self._current_file.getparams()

def open(filenames):
    """open a sequence of filenames as a single WavSequence object
    """
    seq = WavSequence(filenames)
    seq.open()
    return seq
