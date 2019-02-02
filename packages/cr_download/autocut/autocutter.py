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
import wave
from collections import deque

from progressbar import progressbar

from .. import media_utils
from ..configuration import data as config

from . import sample_fingerprint
from . import fingerprint_sequence
from . import wav_sequence

CUT = "C"
KEEP = "K"

DEBUG = False

class AutocutterException(Exception):
    """exception thrown when there are problems preventing an audio file
    from being autocut, e.g. if the detected transitions in the audio
    file don't conform to the pattern the autocutter expects.

    """

def fingerprint_transition_times(
        fingerprints, sample_prints,
        transition_sequence,
        window_time=10.0):

    """identify indices in a fingerprint array where transition
    soundtracks start/stop.

    return an array of pairs marking the beginnings/ends of segments
    of the array which lie between transition soundtracks.

    """

    transition_indices = []
    sequence = deque(transition_sequence)
    expected_sample = sequence.popleft()
    transitioning = False

    ashift_frame_ct = 0
    ashift_frame_start = 0

    print("Finding transition times...")
    for i, window in progressbar(
            enumerate(fingerprints.windows(window_time=window_time))):

        error = sample_prints[expected_sample].window_error(window)

        if ((transitioning and error > config.autocut_error_threshold) or
            ((not transitioning) and (error < config.autocut_error_threshold))):
            if ashift_frame_ct == 0:
                ashift_frame_start = i * fingerprints.window_size(window_time)
            ashift_frame_ct += 1
        else:
            ashift_frame_ct = 0

        if ashift_frame_ct >= config.autocut_time_threshold:
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
    for name, intervals in progressbar(episode_segments):
        wavfile_name = os.path.join(
            output_dir,
            media_utils.change_ext(os.path.basename(name), ".wav"))

        output_wav = wave.open(wavfile_name, "wb")
        output_wav.setparams(input_audio.getparams())
        for start, end in intervals:
            input_audio.skip_frames(start - current_frame)
            if end == -1:
                input_audio.copy_to_end(output_wav)
                break
            else:
                input_audio.copy_frames(end - start, output_wav)
                current_frame = end

        media_utils.ffmpeg_convert(wavfile_name, name)
        edited_files.append(name)

    input_audio.close()

    return edited_files

def get_transition_times(audio_files, transition_sequence, window_time=10):
    """get a sequence of timestamps for points in audio files where
    transitions are found.

    """
    sample_prints = sample_fingerprint.load_prints(
        sample_file=config.sample_data_file
    )

    print("Generating audio fingerprints...")
    fingerprints = fingerprint_sequence.load_fingerprints(
        audio_files, use_cache=config.use_cache)

    fp_transitions = fingerprint_transition_times(
        fingerprints, sample_prints, transition_sequence,
        window_time=window_time
    )

    pcm_transitions = [fingerprints.index_to_pcm(index)
                       for index in fp_transitions]

    return pcm_transitions

def _get_episode_partname(episode_pattern, part_index):
    if "*" in episode_pattern:
        ep_name = episode_pattern.replace(
            "*", "{:02d}".format(part_index), 1
        )
    else:
        base, ext = os.path.splitext(episode_pattern)
        ep_name = base + "_{:02d}".format(part_index) + ext

    return ep_name


def autocut(audio_files, output_file):
    """automatically edit the array of audio files to exclude transitions
    and specific segments between them.

    if config.autocut_merge is specified, a single audio file is
    produced, with undesired segments excluded. Otherwise, one audio
    file for each desired segment is created.

    returns the name(s) of the created file(s).

    """

    if config.cutting_sequence:
        cutting_sequence = config.cutting_sequences[config.cutting_sequence]
    else:
        cutting_sequence = config.cutting_sequences[
            config.default_cutting_sequence
        ]

    pcm_intervals = intervals_to_keep(
        get_transition_times(audio_files,
                             config.audio_sequences[config.audio_sequence]),
        cutting_sequence
    )

    if config.autocut_merge:
        episode_segments = [(output_file, pcm_intervals)]
    else:
        episode_segments = [
            (_get_episode_partname(output_file, i), [interval])
            for i, interval in enumerate(pcm_intervals)
        ]

    tmpdir = tempfile.mkdtemp()
    try:
        output_files = recut_files(audio_files, tmpdir, episode_segments)
    finally:
        if (not DEBUG and not config.debug):
            shutil.rmtree(tmpdir)
        else:
            print(("Debug mode: autocutter preserving temporary directory "
                   "{}".format(tmpdir)))
    return output_files

def get_autocut_errors(audio_files, window_time=10.0):
    """get an array of the minimum bit diffs found in the fingerprint
    array for audio_files and the sample transition arrays

    """
    sample_prints = sample_fingerprint.load_prints(
        sample_file=config.sample_data_file
    )

    fingerprints = fingerprint_sequence.FingerprintSequence(audio_files)

    errors = []
    for window in progressbar(fingerprints.windows(window_time=window_time)):

        error = min([spr.window_error(window)
                     for spr in sample_prints.values()])
        errors.append(error)

    return errors

def autocut_file(input_file, output_file, debug=False):
    """helper function (not used) to autocut a single audio file

    """
    edited_files = []
    tmpdir = tempfile.mkdtemp()
    try:
        audio_files = media_utils.mp4_to_audio_segments(
            input_file, tmpdir, ".wav")
        edited_files = autocut(audio_files, output_file)
    finally:
        if not debug and not DEBUG:
            shutil.rmtree(tmpdir)

    return edited_files
