from __future__ import print_function
from future.utils import iteritems
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
    pass

class AudioException(Exception):
    pass

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

    if chunk_index < len(chunks):
        window = chunks[chunk_index][chunk_pt:chunk_pt + size]
        chunk_pt += size
        if len(window) < size and chunk_index + 1 < len(chunks):
            diff = size - len(window)
            window += chunks[1 + chunk_index][:diff]
            chunk_index += 1
            chunk_pt = diff

        yield window


def fingerprint_transition_times(
        fingerprint_chunks, sample_prints,
        cutting_pattern=None,
        transition_sequence=None,
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

    if transition_sequence is None:
        transition_sequence = cr_settings.DATA["audio_sequences"][
            cr_settings.DATA["default_audio_sequence"]
        ]

    if cutting_pattern is None:
        cutting_pattern = cr_settings.DATA["cutting_sequences"][
            cr_settings.DATA["default_cutting_sequence"]
        ]

    to_keep = []
    sequence = deque(transition_sequence)
    pattern = deque(cutting_pattern)
    expected_sample = sequence.popleft()
    transitioning = False
    state = pattern.popleft()

    interval_start = 0
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
            if state == KEEP:
                to_keep.append((interval_start, ashift_frame_start))

            if not pattern or not sequence:
                return to_keep

            state = pattern.popleft()
            if state == KEEP:
                interval_start = ashift_frame_start

            transitioning = not transitioning
            ashift_frame_ct = 0
            if not transitioning:
                expected_sample = sequence.popleft()

    if pattern or sequence:
        raise AutocutterException("Did not find the full expected transition sequence")
    return to_keep

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
            raise AudioException(
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
    current = input_file.tell()
    clamped_transitions = [
        (autocutter_utils.clamp(start - start_index, 0, num_frames),
         autocutter_utils.clamp(end - start_index, 0, num_frames))
        for start, end in transitions
    ]

    output_file = wave.open(outfile_name, "wb")
    output_file.setparams(input_file.getparams())

    for start, end in clamped_transitions:
        input_file.readframes(start - current)
        output_file.writeframes(input_file.readframes(end - start))
        total_written += end - start
        current = end

    output_file.close()

    return total_written

def recut_files(input_files, output_dir, transition_times, pattern,
                merge=False):
    """Cut out unwanted portions of an array of audio files.

    TRANSITION_TIMES marks the endpoints kept portions of the array as
    sample indices.

    PATTERN is either the name of the final output file or a pattern
    containing a wildcard character (*), which will be substituted
    with the index of each recut segment to obtain the names of the
    output files.

    return the names of the audio files created.

    """
    start_index = 0

    if not autocutter_utils.valid_pattern(pattern) and not merge:
        raise Exception("improper split pattern: {}".format(pattern))

    if merge:
        names = [(pattern, transition_times)]
    else:
        names = [
            (pattern.replace("*", str(i)), [endpts])
            for i, endpts in enumerate(transition_times)
        ]

    oput_dirs = {name:os.path.join(output_dir, os.path.basename(name))
                 for name, _ in names}

    for oput_dir in oput_dirs.values():
        os.mkdir(oput_dir)

    edited_files = {name:[] for name, _ in names}
    for infile in tqdm(input_files):
        outfile_basename = media_utils.change_ext(
            os.path.basename(infile),
            ".wav"
        )
        input_audio = wave.open(infile, "rb")
        for name, transitions in names:

            outfile_name = os.path.join(oput_dirs[name], outfile_basename)
            frames = write_transitions(input_audio, outfile_name,
                                       transitions, start_index)

            if frames > 0:
                edited_files[name].append(outfile_name)
        start_index += input_audio.getnframes()
        input_audio.close()

    for output, contents in edited_files.iteritems():
        media_utils.merge_audio_files(contents, output)
    return list(edited_files)

def autocut(audio_files, output_file, window_time=10.0,
            cutting_sequence="default", debug=False,
            merge_segments=False):
    """automatically edit the array of audio files to exclude transitions
    and specific segments between them.

    if MERGE_SEGMENTS is specified, a single audio file is produced,
    with undesired segments excluded. Otherwise, one audio file for
    each desired segment is created.

    returns the name(s) of the created file(s).
    """
    sample_prints = sample_fingerprint.load_prints(
        sample_file=cr_settings.DATA["sample_data_file"]
    )

    (fingerprints, total_duration,
     samplerate, channels) = load_fingerprints(audio_files)

    total_print_len = sum([len(chunk) for chunk in fingerprints])

    fingerprint_rate = total_print_len / total_duration
    fingerprint_window_size = int(window_time * fingerprint_rate)


    cutting_pattern = cr_settings.DATA["cutting_sequences"].get(
        cutting_sequence
    )

    fp_transitions = fingerprint_transition_times(
        fingerprints, sample_prints, cutting_pattern,
        window_size=fingerprint_window_size
    )

    pcm_transitions = [(int(samplerate * start / fingerprint_rate),
                        int(samplerate * end / fingerprint_rate))
                       for start, end in fp_transitions]

    tmpdir = tempfile.mkdtemp()
    try:
            output_files = recut_files(audio_files, tmpdir, pcm_transitions,
                                       output_file, merge = merge_segments)
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

def autocut_file(input_file, output_file, window_time=10.0,
                 debug=False):
    """helper function (not used) to autocut a single audio file

    """
    tmpdir = tempfile.mkdtemp()
    try:
        audio_files = media_utils.mp4_to_audio_segments(
            input_file, tmpdir, ".wav")
        autocut(audio_files, output_file, window_time)
    finally:
        if not debug and not DEBUG:
            shutil.rmtree(tmpdir)
