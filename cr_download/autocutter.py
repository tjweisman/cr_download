import os
from itertools import chain
from collections import deque
import pickle
import subprocess
import re
import tempfile
import shutil

import numpy as np
import essentia.standard as es
import acoustid
from tqdm import tqdm

import media_utils
import cr_settings
from autocutter_utils import *

CUT = 0
KEEP = 1

MASK = 0xFF000000
SAMPLE_RATE = 44100.0
MAX_CHUNK_SIZE = 500

SAMPLE_FINGERPRINT = "sample_fingerprints"
SAMPLE_FILES = {
    "overture" : "overture.mp3",
    "intro" : "Critical Role Campaign 2 Intro.mp3",
    "dndbeyond" : "DD Beyond Official Theme.mp3"
}

CUTTING_PATTERN = [CUT, CUT, KEEP, CUT, KEEP, CUT, CUT, CUT, KEEP, CUT]
BASE_SEQUENCE = ["overture", "intro", "dndbeyond", "overture", "overture"]

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


#TODO: keep these stored so I'm not recomputing the chromaprints every time
def load_sample_prints(mask = MASK, pickle_file = None):
    if pickle_file is not None:
        pickle_fi = os.path.join(cr_settings.CONFIG_DIR, pickle_file)
        try:
            with open(pickle_fi, "r") as pfi:
                prints = pickle.load(pfi)
            return prints
        except IOError:
            print("Could not open samples from {}. ".format(pickle_file) +
                  "Regenerating fingerprints...")
            
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
        print("Writing fingerprints to {}...".format(pickle_fi))
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

def next_window(chunks, index, size):
    chunk_size = len(chunks[0])
    i = index / chunk_size
    j = index % chunk_size

    if i < chunk_size:
        window = chunks[i][j:j + size]
        if len(window) < size and i + 1 < len(chunks):
            diff = size - len(window)
            window += chunks[1 + i][:diff]
        
        return window
    else:
        return None
    
def fingerprint_transition_times(fingerprint_chunks, sample_prints,
                                 transition_sequence = BASE_SEQUENCE,
                                 cutting_pattern = CUTTING_PATTERN,
                                 threshold = 0.2, window_size = 40):

    to_keep = []
    sequence = deque(transition_sequence)
    pattern = deque(cutting_pattern)
    expected_sample = sequence.popleft()
    transitioning = False
    state = pattern.popleft()
    interval_start = 0

    total_length = sum([len(chunk) for chunk in fingerprint_chunks])
    
    print("Finding transition times...")
    for i in tqdm(range(0, total_length, window_size)):
        
        print_window = next_window(fingerprint_chunks, i, window_size)
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



def recut_files(input_files, transition_times):
    start_index = 0
    edited_files = []
    for infile in tqdm(sorted(input_files.keys())):
        loader = es.AudioLoader(filename = infile)
        audio, sample_rate, channels, md5, bitrate, codec = loader()
        
        s_transitions = [(clamp(start - start_index, 0, len(audio)),
                          clamp(end - start_index, 0, len(audio)))
                               for start, end in transition_times]

        
        to_include = np.vstack([audio[s:e] for s,e in s_transitions])
        
        if len(to_include) > 0:
            writer = es.AudioWriter(filename = input_files[infile])
            writer(to_include)
            edited_files.append(input_files[infile])
            
        start_index += len(audio)
        
    return edited_files



def autocut(audio_files, output_file, window_time = 10.0):
    sample_prints = load_sample_prints(pickle_file=SAMPLE_FINGERPRINT)
    
    fingerprints, total_length = load_fingerprints(audio_files)
    total_print_len = sum([len(chunk) for chunk in fingerprints])

    fingerprint_len = total_length / total_print_len
    fingerprint_window = int(window_time * SAMPLE_RATE / fingerprint_len)

    fp_transitions = fingerprint_transition_times(fingerprints,
                                                  sample_prints)
    
    pcm_transitions = [(s * fingerprint_len,
                        e * fingerprint_len) for s,e in fp_transitions]

    tmpdir = tempfile.mkdtemp()
    
    repl_dict = {}
    for infile in audio_files:
        base = os.path.basename(infile)
        tbase = media_utils.change_ext(base, ".wav")
        repl_dict[infile] = os.path.join(tmpdir, tbase)

    to_concat = recut_files(repl_dict, pcm_transitions)
    media_utils.merge_audio_files(to_concat, output_file)
    
    shutil.rmtree(tmpdir)

def autocut_pattern(input_dir, input_pattern, output_file,
                    window_time = 10.0):
    audio_files = media_utils.file_list(input_dir, input_pattern)
    autocut(audio_files, output_file, window_time)
