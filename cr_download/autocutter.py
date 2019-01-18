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
from itertools import chain
from collections import deque

import wave
from tqdm import tqdm

from . import media_utils
from . import cr_settings

from . import autocutter_utils
from . import sample_fingerprint

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

def window_error(window_print, sample_print, check_high_bits=True):
    """find minimum pct bit error for a short fingerprint segment compared
    to the fingerprint of a transition soundtrack.

    we slide the window across the sample, computing percent bit
    errors, and take the minimum. If CHECK_HIGH_BITS is specified, do
    a first pass so we only check points where the high-order bits of
    the sample/window agree.
    """
    offsets = range(len(sample_print) - len(window_print))
    if check_high_bits:
        masked_prints = {prt & sample_print.mask for prt in window_print}
        intersect = masked_prints & sample_print.masked_prints_s
        offsets = chain(*[sample_print.masked_prints_i[val]
                          for val in intersect])

    errs = [autocutter_utils.total_error(
        window_print, sample_print.fingerprint[offset:]) for
            offset in offsets]

    if not errs:
        return 1.0

    return min(errs)

def fingerprint_windows(chunks, size):
    """generator for a sequence of fixed-size windows in an array of
    fingerprint arrays

    """
    chunk_index = 0
    chunk_pt = 0

    while chunk_index < len(chunks):
        window = chunks[chunk_index][chunk_pt:chunk_pt + size]
        chunk_pt += size
        if chunk_pt >= len(chunks[chunk_index]):
            chunk_index += 1
            if chunk_index < len(chunks):
                diff = size - len(window)
                window += chunks[chunk_index][:diff]
                chunk_pt = diff

        yield window


def fingerprint_transition_times(
        fingerprint_chunks, sample_prints,
        transition_sequence,
        error_threshold=DEFAULT_ERROR_THRESHOLD,
        time_threshold=DEFAULT_TIME_THRESHOLD,
        window_size=40):
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
    for i, window in tqdm(enumerate(fingerprint_windows(
            fingerprint_chunks, window_size))):

        error = window_error(window, sample_prints[expected_sample])

        if ((transitioning and error > error_threshold) or
            ((not transitioning) and (error < error_threshold))):
            if ashift_frame_ct == 0:
                ashift_frame_start = i * window_size
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

def load_fingerprints(audio_files):
    """load an array of audio files and compute their chromaprints
    """
    total_duration = 0.0
    prints = []

    samplerate = None
    channels = None
    print("Loading and fingerprinting audio files...")
    for filename in tqdm(audio_files):
        fingerprint, data = autocutter_utils.fingerprint_full_file(filename)
        total_duration += data["duration"]
        if ((channels is not None and data["channels"] != channels) or
            (samplerate is not None and data["samplerate"] != samplerate)):
            raise AutocutterException(
                "Autocutter doesn't know how to handle input files "
                "with different channelno or sample rate!"
            )
        else:
            channels = data["channels"]
            samplerate = data["samplerate"]
        prints.append(fingerprint)

    return (prints, total_duration, samplerate, channels)

def write_transitions(input_file, outfile_name, transitions, start_index):
    """write the segments of the wav file in INPUT specified in
    TRANSITIONS to a new wav file.

    START_INDEX specifies the offset to use for the transitions.

    """
    total_written = 0

    num_frames = input_file.getnframes()
    #FIXME: DON'T USE TELL, THIS IS IMPLEMENTATION DEPENDENT
    current = input_file.tell()
    clamped_transitions = [
        (autocutter_utils.clamp(start - start_index, 0, num_frames),
         autocutter_utils.clamp(end - start_index, 0, num_frames))
        for start, end in transitions
    ]

    output_file = wave.open(outfile_name, "wb")
    output_file.setparams(input_file.getparams())

    for start, end in clamped_transitions:
        #TODO: use a fixed-size buffer so we don't read a massive array
        input_file.readframes(start - current)
        #TODO: use a fixed-size buffer and handle the case end = -1
        output_file.writeframes(input_file.readframes(end - start))
        total_written += end - start
        current = end

    output_file.close()

    return total_written

def recut_files(input_files, output_dir, episode_segments):
    """Cut out unwanted portions of an array of audio files.

    EPISODE_SEGMENTS is a sequence of tuples, indicating portions to
    cut the episode up into, of the form (part_name, intervals). I
    should probably have an "episode segment" class or something
    instead.

    Each value in the dictionary is an array of intervals belonging to
    that segment.

    return the names of the audio files created.

    """
    start_index = 0

    for name, _ in episode_segments:
        os.mkdir(os.path.join(output_dir, os.path.basename(name)))

    edited_files = {name:[] for name, _ in episode_segments}

    for infile in tqdm(input_files):
        outfile_basename = media_utils.change_ext(
            os.path.basename(infile),
            ".wav"
        )
        input_audio = wave.open(infile, "rb")
        for name, transitions in episode_segments:
            outfile_name = os.path.join(output_dir,
                                        os.path.basename(name),
                                        outfile_basename)

            frames = write_transitions(input_audio, outfile_name,
                                       transitions, start_index)

            if frames > 0:
                edited_files[name].append(outfile_name)
        start_index += input_audio.getnframes()
        input_audio.close()

    for output, contents in edited_files.items():
        media_utils.merge_audio_files(contents, output)

    return list(edited_files)

def get_transition_times(audio_files, transition_sequence, window_time=10.0):
    """get a sequence timestamps for points in audio files where
    transitions are found.

    """
    sample_prints = sample_fingerprint.load_prints(
        sample_file=cr_settings.DATA["sample_data_file"]
    )

    (fingerprints, total_duration,
     samplerate, channels) = load_fingerprints(audio_files)

    total_print_len = sum([len(chunk) for chunk in fingerprints])

    fingerprint_rate = total_print_len / total_duration
    fingerprint_window_size = int(window_time * fingerprint_rate)

    fp_transitions = fingerprint_transition_times(
        fingerprints, sample_prints, transition_sequence,
        window_size=fingerprint_window_size
    )

    pcm_transitions = [int(samplerate * index / fingerprint_rate)
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

    (fingerprints, total_duration,
     _, _) = load_fingerprints(audio_files)

    total_len = sum([len(chunk) for chunk in fingerprints])

    fingerprint_rate = total_len / total_duration
    window_size = int(window_time * fingerprint_rate)

    errors = []
    for window in tqdm(fingerprint_windows(fingerprints, window_size)):

        error = min([window_error(window, spr)
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
