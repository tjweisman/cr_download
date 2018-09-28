import os
from itertools import chain
from collections import deque
import pickle
import subprocess

import numpy as np
import essentia.standard as es
import acoustid
from tqdm import tqdm

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
        try:
            with open(pickle_file, "r") as pfi:
                prints = pickle.load(pfi)
            return prints
        except IOError:
            print("Could not open samples from {}. ".format(pickle_file) +
                  "Regenerating fingerprints...")
            
    prints = {}
    mono_loader = es.MonoLoader()
    cp = es.Chromaprinter()
    for key, filename in SAMPLE_FILES.iteritems():
        mono_loader.configure(filename = os.path.join("break_sounds", filename))
        sample_audio_print = cp(mono_loader())
        fingerprints = acoustid.chromaprint.decode_fingerprint(
            sample_audio_print)[0]
        prints[key] = SampleFingerprint(fingerprints, mask)

    if pickle_file != None:
        print("Writing fingerprints to {}...".format(pickle_file))
        with open(pickle_file, "w") as pfi:
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

def load_audio_data(audio_file,
                    test_mono = None,
                    test_stereo = None,
                    test_print = None):
    
    stereo_audio = test_stereo
    mono_audio = test_mono
    audio_print = test_print

    stereo_loader = es.AudioLoader()
    cp = es.Chromaprinter()
    mix = es.MonoMixer()

    if (test_mono == None or
        test_stereo == None or
        test_print == None):
        print("Loading audio file...")
        stereo_loader.configure(filename = audio_file)
        (stereo_audio, sample_rate, channels,
         md5, bitrate, codec) = stereo_loader()
        print("Downmixing...")
        mono_audio = mix(stereo_audio, channels)

    return (stereo_audio, mono_audio)

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
    loader = es.AudioLoader()
    writer = es.AudioWriter()
    start_index = 0

    for infile in tqdm(sorted(input_files.keys())):
        loader.configure(filename = infile)
        audio, sample_rate, channels, md5, bitrate, codec = loader()
        s_transitions = [(max(start - start_index, 0),
                                min(end - start_index), len(audio))
                               for start, end in transition_times]
        
        to_include = np.vstack([audio[s:e] for s,e in s_transitions])
        if len(to_include) > 0:
            writer.configure(filename = input_files[infile])
            writer(to_include)
        

def autocut(audio_file, output, window_time = 10.0):
    sample_prints = load_sample_prints(pickle_file=SAMPLE_FINGERPRINT)
    
    audio_files = file_list("mp3_files", "{}.*mp3".format(audio_file))
    fingerprints, total_length = load_fingerprints(audio_files)
    total_print_len = sum([len(chunk) for chunk in fingerprints])

    fingerprint_len = total_length / total_print_len
    fingerprint_window = int(window_time * SAMPLE_RATE / fingerprint_len)

    fp_transitions = fingerprint_transition_times(fingerprints,
                                                  sample_prints)
    
    pcm_transitions = [(s * fingerprint_len,
                        e * fingerprint_len) for s,e in fp_transitions]

    repl_dict = {infile:infile.replace(".mp3", ".wav") for infile in audio_files}
    recut_files(audio_files, pcm_transitions)
    
