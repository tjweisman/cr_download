import acoustid
import audioread

def invert(arr):
    iv = {}
    for i, v in enumerate(arr):
        iv.setdefault(v, []).append(i)
    return iv

def get_bitcount_table():
    return ["{0:b}".format(i).count("1") for i in range(2**8)]

bit_table = get_bitcount_table()

def countbits(b):
    return (bit_table[(b >> 0)  & 0xFF] +
            bit_table[(b >> 8)  & 0xFF] +
            bit_table[(b >> 16) & 0xFF] +
            bit_table[(b >> 24) & 0xFF])

def total_error(print1, print2):
    err = sum([countbits(b1 ^ b2) for b1, b2 in zip(print1,
                                                    print2)])
    return float(err) / (32 * min(len(print1), len(print2)))

def clamp(val, mn, mx):
    return min(max(val, mn), mx)

def valid_pattern(pattern):
    return pattern.count("*") == 1

def fingerprint_full_file(filename):
    """read an audio file and compute its full chromaprint
    """
    with audioread.audio_open(filename) as f:
        data = {"duration":f.duration,
                "samplerate":f.samplerate,
                "channels":f.channels}
        fp = acoustid.fingerprint(
            f.samplerate, f.channels, iter(f), f.duration
        )
        fprint = acoustid.chromaprint.decode_fingerprint(fp)[0]
    return fprint, data

