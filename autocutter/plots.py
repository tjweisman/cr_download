import os
import re

import matplotlib.pyplot as plt
import essentia.standard
import numpy as np

FRAME_SIZE = 1024

file_loader = essentia.standard.MonoLoader()
w = essentia.standard.Windowing(type = "hann")
frame_cutter = 
spectrum = essentia.standard.Spectrum()
mmg = essentia.standard.MaxMagFreq()

def get_frames_from_file(audio_file):
    file_loader.configure(filename = audio_file)
    audio_data = file_loader()

    #truncate array so numpy splits it correctly
    #TODO: use the goddamn frame cutter
    audio_data = audio_data[:-1 * (len(audio_data) % FRAME_SIZE)]
    pieces = len(audio_data) / FRAME_SIZE
    
    return np.split(audio_data, pieces)

def get_frames_from_files(file_list):
    frames = []
    for filename in file_list:
        print("processing {}...".format(filename))
        frames += get_frames_from_file(filename)
    return frames

def file_list(directory, pattern):
    files = os.listdir(directory)
    matched_files = sorted([os.path.join(directory, fname)
                            for fname in files
                            if re.match(pattern, fname)])
    return matched_files

def get_file_spectra(directory, pattern):
    frames = get_frames_from_files(file_list(directory, pattern))
    return [spectrum(w(frame)) for frame in frames]
