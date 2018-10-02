import os
import pickle
import subprocess
import re
import tempfile
import shutil
from itertools import chain
from collections import deque

import numpy as np
import essentia.standard as es
import acoustid
from tqdm import tqdm

import media_utils
import cr_settings
from autocutter_utils import *

CUT = 0
KEEP = 1

DEBUG = False

MASK = 0xFF000000
SAMPLE_RATE = 44100.0
MAX_CHUNK_SIZE = 500

SAMPLE_FINGERPRINT = "sample_fingerprints"
SAMPLE_FILES = {
    "overture" : "overture.mp3",
    "intro" : "Critical Role Campaign 2 Intro.mp3",
    "dndbeyond" : "DD Beyond Official Theme.mp3"
}

CUTTING_PATTERN_NO_INTRO = (
    [CUT, CUT, CUT, CUT, KEEP, CUT, CUT, CUT, KEEP, CUT]
)
CUTTING_PATTERN_INTRO = (
    [CUT, CUT, KEEP, CUT, KEEP, CUT, CUT, CUT, KEEP, CUT]
)

BASE_SEQUENCE = ["overture", "intro", "dndbeyond", "overture", "overture"]

class AutocutterException(Exception):
    pass

class SampleFingerprint:
    """class to store fingerprint data for one of the Critical Role
    transition soundtracks

    """
    def __init__(self, fingerprint, mask = MASK):
        self.fingerprint = fingerprint
        self.mask = mask
        masked_prints = [fprint & mask for fprint in fingerprint]
        self.masked_prints_i = invert(masked_prints)
        self.masked_prints_s = set(masked_prints)

    def __len__(self):
        return len(self.fingerprint)


def load_sample_prints(mask = MASK, pickle_file = None):
    """Load transition soundtrack fingerprint data from file(s).

    If PICKLE_FILE is specified, this function tries to load
    fingerprint data from a pickle file stored in the config
    directory.

    If that fails, it will load the actual .mp3 files for transition
    soundtracks from the config directory, regenerate the fingerprint
    data, and save it to the specified pickle file.

    If no PICKLE_FILE is specified, just generate the fingerprint
    data.

    """
    
    print("Loading sample fingerprint data...")
    if pickle_file is not None:
        pickle_fi = os.path.join(cr_settings.CONFIG_DIR, pickle_file)
        try:
            with open(pickle_fi, "r") as pfi:
                prints = pickle.load(pfi)
            return prints
        except IOError:
            print("Could not open samples from {}. ".format(pickle_file))

    print("Generating fingerprints...")
    prints = {}
    mono_loader = es.MonoLoader()
    cp = es.Chromaprinter()
    sample_dir = os.path.join(cr_settings.CONFIG_DIR, "break_sounds")
    
    for key, filename in SAMPLE_FILES.iteritems():
        mono_loader.configure(filename = os.path.join(sample_dir, filename))
        sample_audio_print = cp(mono_loader())
        fingerprints = acoustid.chromaprint.decode_fingerprint(
            sample_audio_print)[0]
        prints[key] = SampleFingerprint(fingerprints, mask)

    if pickle_file != None:
        print("Writing fingerprints to {}...".format(pfi))
        with open(pickle_fi, "w") as pfi:
            pickle.dump(prints, pfi)

    return prints

def window_error(window_print, sample_print, check_high_bits = True):
    """find minimum pct bit error for a short fingerprint segment compared
    to the fingerprint of a transition soundtrack.

    we slide the window across the sample, computing percent bit
    errors, and take the minimum. If CHECK_HIGH_BITS is specified, do
    a first pass so we only check points where the high-order bits of
    the sample/window agree. 
    """
    offsets = range(len(sample_print) - len(window_print))
    if check_high_bits:
        masked_prints = set([prt & sample_print.mask for prt in window_print])
        intersect = masked_prints & sample_print.masked_prints_s
        offsets = chain(*[sample_print.masked_prints_i[val]
                          for val in intersect])

    errs = [total_error(window_print, sample_print.fingerprint[offset:]) for
            offset in offsets]
    
    if len(errs) == 0:
        return 1.0
    
    return min(errs)

def next_window(chunks, chunk_index, chunk_pt, size):
    """get the next fixed-size window in an array of fingerprint arrays

    """
    i = chunk_index
    j = chunk_pt
    if i < len(chunks):
        window = chunks[i][j:j + size]
        j = j + size
        if len(window) < size and i + 1 < len(chunks):
            diff = size - len(window)
            window += chunks[1 + i][:diff]
            i = i + 1
            j = diff
        
        return (window, i, j)
    else:
        return None
    
def fingerprint_transition_times(fingerprint_chunks, sample_prints,
                                 transition_sequence = BASE_SEQUENCE,
                                 cutting_pattern =
                                 CUTTING_PATTERN_INTRO, threshold =
                                 0.2, window_size = 40):
    """identify indices in a fingerprint array where transition
    soundtracks start/stop.

    FINGERPRINT_CHUNKS is (effectively) concatenated and then cut into
    windows, each of which is compared to the soundtracks in SAMPLE
    PRINTS. We return an array of pairs marking the beginnings/ends of
    segments of the array which lie between transition soundtracks
    (and are marked to be kept by CUTTING_PATTERN).
    """
    
    to_keep = []
    sequence = deque(transition_sequence)
    pattern = deque(cutting_pattern)
    expected_sample = sequence.popleft()
    transitioning = False
    state = pattern.popleft()
    interval_start = 0
    chunk_index = 0
    chunk_pt = 0

    total_length = sum([len(chunk) for chunk in fingerprint_chunks])

    print("Finding transition times...")
    for i in tqdm(range(0, total_length, window_size)):
        
        print_window, chunk_index, chunk_pt = next_window(
            fingerprint_chunks, chunk_index, chunk_pt, window_size
        )
        error = window_error(print_window, sample_prints[expected_sample])

        if ((transitioning and error > threshold) or
            ((not transitioning) and (error < threshold))):
            if state == KEEP:
                to_keep.append((interval_start, i))

            if len(pattern) == 0 or len(sequence) == 0:
                return to_keep

            state = pattern.popleft()
            if state == KEEP:
                interval_start = i

            transitioning = not transitioning
            if not transitioning:
                expected_sample = sequence.popleft()
    if len(pattern) > 0 or len(sequence) > 0:
        raise AutocutterException("Did not find the full expected transition sequence")
    return to_keep

def load_fingerprints(audio_files):
    """load an array of audio files and compute their chromaprints
    """
    loader = es.MonoLoader()
    cp = es.Chromaprinter()
    total_len = 0
    prints = []

    print("Loading audio files...")
    for filename in tqdm(audio_files):
        loader.configure(filename = filename)
        raw_audio = loader()
        total_len += len(raw_audio)
        prints.append(acoustid.chromaprint.decode_fingerprint(
            cp(raw_audio))[0])

    return (prints, total_len)

def load_stereo_audio(audio_file):
    loader = es.AudioLoader(filename = audio_file)
    audio, sample_rate, channels, md5, bitrate, codec = loader()
    return audio

def audio_segments(audio, transitions, start_index):
    clamped_transitions =  [(clamp(start - start_index, 0, len(audio)),
                             clamp(end - start_index, 0, len(audio)))
                            for start, end in transitions]
    return [audio[s:e] for s,e in clamped_transitions]
                           

def write_recut_audio(audio, infile, output_dir):
    """write audio data to a renamed version of INFILE located in
    OUTPUT_DIR

    """
    outfile_base = media_utils.change_ext(
        os.path.basename(infile),
        ".wav")
    outfile = os.path.join(output_dir, outfile_base)
            
    writer = es.AudioWriter(filename = outfile)
    writer(audio)
    return outfile

def recut_files(input_files, output_dir, transition_times, pattern,
                merge = False):
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

    if not valid_pattern(pattern) and not merge:
        raise Exception("improper split pattern: {}".format(pattern))
    if merge:
        names = [pattern]
    else:
        names = [
            pattern.replace("*", str(i))
            for i, _ in enumerate(transition_times)
        ]
        
    oput_dirs = {name:os.path.join(output_dir, os.path.basename(name))
                  for name in names}
        
    for oput_dir in oput_dirs.values():
        os.mkdir(oput_dir)
            
    edited_files = {name:[] for name in names}
    
    for infile in tqdm(input_files):
        audio = load_stereo_audio(infile)
        to_include = audio_segments(audio, transition_times, start_index)
        
        if merge:
            to_include = [np.vstack(to_include)]
            
        for cut_audio, name in zip(to_include, names):
            if len(cut_audio) > 0:
                outfile = write_recut_audio(cut_audio,
                                            infile,
                                            oput_dirs[name])
                edited_files[name].append(outfile)
        start_index += len(audio)

    for output, contents in edited_files.iteritems():
        media_utils.merge_audio_files(contents, output)
    return edited_files.keys()


def autocut(audio_files, output_file, window_time = 10.0, keep_intro=False,
            debug=False, merge_segments = False):
    """automatically edit the array of audio files to exclude transitions
    and specific segments between them.

    if MERGE_SEGMENTS is specified, a single audio file is produced,
    with undesired segments excluded. Otherwise, one audio file for
    each desired segment is created.

    returns the name(s) of the created file(s).
    """
    sample_prints = load_sample_prints(pickle_file=SAMPLE_FINGERPRINT)
    
    fingerprints, total_length = load_fingerprints(audio_files)
    total_print_len = sum([len(chunk) for chunk in fingerprints])

    fingerprint_len = float(total_length) / total_print_len
    fingerprint_window = int(window_time * SAMPLE_RATE / fingerprint_len)

    if keep_intro:
        cutting_pattern = CUTTING_PATTERN_INTRO
    else:
        cutting_pattern = CUTTING_PATTERN_NO_INTRO
        
    fp_transitions = fingerprint_transition_times(
        fingerprints, sample_prints,
        window_size = fingerprint_window,
        cutting_pattern = cutting_pattern
    )
    
    pcm_transitions = [(int(s * fingerprint_len),
                        int(e * fingerprint_len)) for s,e in fp_transitions]

    tmpdir = tempfile.mkdtemp()
    try:
            output_files = recut_files(audio_files, tmpdir, pcm_transitions,
                                       output_file, merge = merge_segments)
    finally:
        if (not DEBUG and not debug):
            shutil.rmtree(tmpdir)
        else:
            print("Debug mode: autocutter preserving temporary directory "
                  "{}".format(tmpdir))            
    return output_files

def autocut_file(input_file, output_file, window_time = 10.0):
    tmpdir = tempfile.mkdtemp()
    try:
        file_segments = media_utils.mp4_to_audio_segments(
            input_file, tmpdir, ".wav")
        autocut(audio_files, output_file, window_time)
    finally:
        shutil.rmtree(tmpdir)
        
