"""autocutter.py

Tools to automatically cut one or more .wav files representing a
single Critical Role episode into segments, based on detected
transitions in the audio sequence.

"""

from __future__ import print_function
from builtins import dict

import os
import tempfile
import shutil
from collections import deque

import wave
from tqdm import tqdm

from . import media_utils
from . import cr_settings

from . import sample_fingerprint
from . import fingerprint_sequence
from . import wav_sequence

CUT = "C"
KEEP = "K"

DEBUG = False

DEFAULT_ERROR_THRESHOLD = 0.22
DEFAULT_TIME_THRESHOLD = 2


class AutocutterException(Exception):
    """exception thrown when there are problems preventing an audio file
    from being autocut, e.g. if the detected transitions in the audio
    file don't conform to the pattern the autocutter expects.

    """

def fingerprint_transition_times(
        fingerprints, sample_prints,
        transition_sequence,
        error_threshold=DEFAULT_ERROR_THRESHOLD,
        time_threshold=DEFAULT_TIME_THRESHOLD,
        window_time=10.0):

    """identify indices in a fingerprint array where transition
    soundtracks start/stop.

    FINGERPRINT_CHUNKS is (effectively) concatenated and then cut into
    windows, each of which is compared to the soundtracks in SAMPLE
    PRINTS. We return an array of pairs marking the beginnings/ends of
    segments of the array which lie between transition soundtracks
    (and are marked to be kept by CUTTING_PATTERN).
    """

    transition_indices = []
    sequence = deque(transition_sequence)
    expected_sample = sequence.popleft()
    transitioning = False

    ashift_frame_ct = 0
    ashift_frame_start = 0

    print("Finding transition times...")
    for i, window in tqdm(
            enumerate(fingerprints.windows(window_time=window_time))):

        error = sample_prints[expected_sample].window_error(window)

        if ((transitioning and error > error_threshold) or
            ((not transitioning) and (error < error_threshold))):
            if ashift_frame_ct == 0:
                ashift_frame_start = i * fingerprints.window_size(window_time)
            ashift_frame_ct += 1
        else:
            ashift_frame_ct = 0

        if ashift_frame_ct >= time_threshold:
            ashift_frame_ct = 0
            transition_indices.append(ashift_frame_start)

            if not sequence:
                break

            transitioning = not transitioning
            if not transitioning:
                expected_sample = sequence.popleft()

    if sequence:
        raise AutocutterException("Did not find the full expected transition sequence")

    return transition_indices

def intervals_to_keep(transition_times, cutting_pattern):
    """convert a sequence of transition timestamps into a sequence of
    timestamp intervals to retain when cutting an episode.

    cutting_pattern: an array of CUT/KEEP values, indicating whether
    to cut or keep the interval between each pair of consecutive
    timestamps

    """
    intervals = []
    transition_index = 0
    transition_times = [0] + transition_times + [-1]

    for segment in cutting_pattern:
        if transition_index + 1 >= len(transition_times):
            raise AutocutterException(
                """Expected transition sequence does not match the
                provided cutting pattern!"""
            )
        if segment == KEEP:
            intervals.append((transition_times[transition_index],
                              transition_times[transition_index + 1]))
        transition_index += 1

    return intervals

def recut_files(input_files, output_dir, episode_segments):
    """Cut out unwanted portions of an array of audio files.

    EPISODE_SEGMENTS is a sequence of tuples, indicating portions to
    cut the episode up into, of the form (part_name, intervals). I
    should probably have an "episode segment" class or something
    instead.

    Each the second value in the tuple is an array of intervals
    belonging to that segment.

    return the names of the audio files created.

    """

    edited_files = []

    input_audio = wav_sequence.open(input_files)
    current_frame = 0
    print("recutting files...")
    #wrap the wav_sequence in a progress bar somehow?
    for name, intervals in tqdm(episode_segments):
        output_name = os.path.join(
            output_dir,
            media_utils.change_ext(os.path.basename(name), ".wav"))

        edited_files.append(output_name)

        output_file = wave.open(output_name, "wb")
        output_file.setparams(input_audio.getparams())
        for start, end in intervals:
            input_audio.skip_frames(start - current_frame)
            if end == -1:
                input_audio.copy_to_end(output_file)
                break
            else:
                input_audio.copy_frames(end - start, output_file)
                current_frame = end

    input_audio.close()

    return edited_files

def get_transition_times(audio_files, transition_sequence, window_time=10):
    """get a sequence of timestamps for points in audio files where
    transitions are found.

    """
    sample_prints = sample_fingerprint.load_prints(
        sample_file=cr_settings.DATA["sample_data_file"]
    )

    print("Generating audio fingerprints...")
    #TODO: find out how to import the class directly
    fingerprints = fingerprint_sequence.load_fingerprints(
        audio_files, use_cache=True)

    fp_transitions = fingerprint_transition_times(
        fingerprints, sample_prints, transition_sequence,
        window_time=window_time
    )

    pcm_transitions = [fingerprints.index_to_pcm(index)
                       for index in fp_transitions]

    return pcm_transitions


def autocut(audio_files, output_file,
            cutting_sequence=None,
            transition_sequence=None,
            debug=False, merge_segments=False):
    """automatically edit the array of audio files to exclude transitions
    and specific segments between them.

    if MERGE_SEGMENTS is specified, a single audio file is produced,
    with undesired segments excluded. Otherwise, one audio file for
    each desired segment is created.

    returns the name(s) of the created file(s).
    """

    if cutting_sequence is None:
        cutting_sequence = cr_settings.DATA["default_cutting_sequence"]

    if transition_sequence is None:
        transition_sequence = cr_settings.DATA["default_audio_sequence"]

    cutting_pattern = cr_settings.DATA["cutting_sequences"].get(
        cutting_sequence)
    audio_sequence = cr_settings.DATA["audio_sequences"].get(
        transition_sequence)

    pcm_intervals = intervals_to_keep(
        get_transition_times(audio_files, audio_sequence),
        cutting_pattern
    )

    if merge_segments:
        episode_segments = [(output_file, pcm_intervals)]
    else:
        episode_segments = [
            (output_file.replace("*", str(i)), [interval])
            for i, interval in enumerate(pcm_intervals)
        ]

    tmpdir = tempfile.mkdtemp()
    try:
        output_files = recut_files(audio_files, tmpdir, episode_segments)
    finally:
        if (not DEBUG and not debug):
            shutil.rmtree(tmpdir)
        else:
            print(("Debug mode: autocutter preserving temporary directory "
                   "{}".format(tmpdir)))
    return output_files

def get_autocut_errors(audio_files, window_time=10.0):
    """get an array of the minimum bit diffs found in the fingerprint
    array for AUDIO_FILES and the sample transition arrays

    """
    sample_prints = sample_fingerprint.load_prints(
        sample_file=cr_settings.DATA["sample_data_file"]
    )

    fingerprints = fingerprint_sequence.FingerprintSequence(audio_files)

    errors = []
    for window in tqdm(fingerprints.windows(window_time=window_time)):

        error = min([spr.window_error(window)
                     for spr in sample_prints.values()])
        errors.append(error)

    return errors

def autocut_file(input_file, output_file, debug=False):
    """helper function (not used) to autocut a single audio file

    """
    tmpdir = tempfile.mkdtemp()
    try:
        audio_files = media_utils.mp4_to_audio_segments(
            input_file, tmpdir, ".wav")
        autocut(audio_files, output_file)
    finally:
        if not debug and not DEBUG:
            shutil.rmtree(tmpdir)
