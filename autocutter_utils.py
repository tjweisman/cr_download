import os
import re
import tempfile

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

def file_list(directory, pattern):
    files = os.listdir(directory)
    matched_files = sorted([os.path.join(directory, fname)
                            for fname in files
                            if re.match(pattern, fname)])
    return matched_files

def merge_audio_files(files, output):
    filelist = tempfile.NamedTemporaryFile()
    for name in files:
        filelist.write("file '{}'\n".format(name))
    subprocess.call(["ffmpeg", "-f", "concat", "-safe", "0", "-i",
                     filelist.name, ep_num])
    filelist.close()

def change_ext(filename, new_ext):
    return re.sub(r"\.[A-z]+$", new_ext, filename)
    
def mp4_to_audio(video_file, output_file,
                 segment=False,
                 segment_fmt=".wav"):
    if segment:
        output_pattern = re.sub(r"\.[A-z]+$",
                                "%03d.{}".format(segment_fmt),
                                video_file)
        subprocess.call(["ffmpeg", "-i", video_file, "-f", "segment",
                         "-segment_time", "1800", output_pattern])
        
        return output_pattern
    else:
        subprocess.call(["ffmpeg", "-i", video_file, output_file])
