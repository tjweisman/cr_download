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

TEST_AUTOCUT_FILENAMES = []

class AutocutterException(Exception):
    pass

class SampleFingerprint:
    def __init__(self, fingerprint, mask = MASK):
        self.fingerprint = fingerprint
        self.mask = mask
        masked_prints = [fprint & mask for fprint in fingerprint]
        self.masked_prints_i = invert(masked_prints)
        self.masked_prints_s = set(masked_prints)

    def __len__(self):
        return len(self.fingerprint)


def load_sample_prints(mask = MASK, pickle_file = None):
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

def write_recut_audio(audio, infile, output_dir):
    outfile_base = media_utils.change_ext(
        os.path.basename(infile),
        ".wav")
    outfile = os.path.join(output_dir, outfile_base)
            
    writer = es.AudioWriter(filename = outfile)
    writer(audio)
    return outfile
            

def recut_files(input_files, output_dir, transition_times,
                split_pattern = None):
    start_index = 0
    edited_files = []

    if split_pattern and not valid_pattern(split_pattern):
        raise Exception("improper split pattern: {}".format(split_pattern))
    if split_pattern:
        split_names = [
            split_pattern.replace("*", str(i))
            for i, _ in enumerate(transition_times)
        ]
        split_dirs = {name:os.path.join(output_dir, os.path.basename(name))
                      for name in split_names}
        
        for split_dir in split_dirs.values():
            os.mkdir(split_dir)
            
        edited_files = {name:[] for name in split_names}
    
    for infile in tqdm(input_files):
        loader = es.AudioLoader(filename = infile)
        audio, sample_rate, channels, md5, bitrate, codec = loader()
        
        s_transitions = [(clamp(start - start_index, 0, len(audio)),
                          clamp(end - start_index, 0, len(audio)))
                               for start, end in transition_times]
        
        to_include = [audio[s:e] for s,e in s_transitions]

        if split_pattern:
            for cut_audio, name in zip(to_include, split_names):
                if len(cut_audio) > 0:
                    outfile = write_recut_audio(cut_audio,
                                                infile,
                                                split_dirs[name])
                    edited_files[name].append(outfile)
        else:
            merged_audio = np.vstack(to_include)
            if len(to_include) > 0:
                outfile = write_recut_audio(merged_audio,
                                            infile,
                                            output_dir)
                edited_files.append(outfile)
        start_index += len(audio)
        
    return edited_files


def autocut(audio_files, output_file, window_time = 10.0, keep_intro=False,
            debug=False, merge_segments = False):
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
        if merge_segments:
            edited_files = recut_files(audio_files, tmpdir, pcm_transitions)
            media_utils.merge_audio_files(edited_files, output_file)
            output_files = [output_file]
        else:
            edited_files = recut_files(audio_files, tmpdir, pcm_transitions,
                                       split_pattern = output_file)
            for output, contents in edited_files.iteritems():
                media_utils.merge_audio_files(contents, output)
            output_files = edited_files.keys()
            
    finally:
        if (not DEBUG and not debug):
            shutil.rmtree(tmpdir)
        else:
            print("Debug mode: autocutter preserving temporary directory "
                  "{}".format(tmpdir))
            
    return edited_files.keys()

def autocut_pattern(input_dir, input_pattern, output_file,
                    window_time = 10.0):
    audio_files = media_utils.file_list(input_dir, input_pattern)
    autocut(audio_files, output_file, window_time)

#TODO: this function needs to be rewritten (although it's convenience
#only so this is low priority)
def autocut_file(input_file, output_file, window_time = 10.0):
    tmpdir = tempfile.mkdtemp()
    base_files = media_utils.mp4_to_audio_segments(input_file, tmpdir, ".wav")
    audio_files = [os.path.join(tmpdir, base) for base in base_files]
    autocut(audio_files, output_file, window_time)
