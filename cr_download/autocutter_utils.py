"""utility functions for the autocutter module
"""

import acoustid
import audioread

def invert(array):
    """return a dictionary mapping array values to arrays of indices
    containing those values

    """
    inverted_array = {}
    for i, val in enumerate(array):
        inverted_array.setdefault(val, []).append(i)
    return inverted_array

def _get_bitcount_table():
    return ["{0:b}".format(i).count("1") for i in range(2**8)]

BIT_TABLE = _get_bitcount_table()

def _countbits(bit_seq):
    return (BIT_TABLE[(bit_seq >> 0)  & 0xFF] +
            BIT_TABLE[(bit_seq >> 8)  & 0xFF] +
            BIT_TABLE[(bit_seq >> 16) & 0xFF] +
            BIT_TABLE[(bit_seq >> 24) & 0xFF])

def total_error(print1, print2):
    """count the percentage of differing bits in a pair of 32-bit vars

    """
    err = sum([_countbits(b1 ^ b2) for b1, b2 in zip(print1,
                                                     print2)])
    return float(err) / (32 * min(len(print1), len(print2)))

def valid_pattern(pattern):
    """return true iff the given string can be used as a pattern of
    filenames to save parts of a critical role episode as

    """
    return pattern.count("*") == 1

def fingerprint_full_file(filename):
    """read an audio file and compute its full chromaprint
    """
    with audioread.audio_open(filename) as audio_file:
        data = {"duration":audio_file.duration,
                "samplerate":audio_file.samplerate,
                "channels":audio_file.channels}
        enc_print = acoustid.fingerprint(
            audio_file.samplerate,
            audio_file.channels,
            iter(audio_file),
            audio_file.duration
        )
        dec_print = acoustid.chromaprint.decode_fingerprint(enc_print)[0]
    return dec_print, data
