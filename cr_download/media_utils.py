import os
import re
import tempfile
import subprocess

def file_list(directory, pattern):
    files = os.listdir(directory)
    matched_files = sorted([os.path.join(directory, fname)
                            for fname in files
                            if re.match(pattern, fname)])
    return matched_files

def merge_audio_files(files, output):
    with tempfile.NamedTemporaryFile() as filelist:
        for name in files:
            filelist.write("file '{}'\n".format(name))
        filelist.flush()
        subprocess.call(["ffmpeg", "-f", "concat", "-safe", "0", "-i",
                         filelist.name, output])

def change_ext(filename, new_ext):
    return re.sub(r"\.\w+$", new_ext, filename)

def mp4_to_audio_segments(video_file, output_dir, segment_fmt):
    basename = os.path.basename(video_file)
    pattern = os.path.join(
        output_dir,
        change_ext(basename, "%03d{}".format(segment_fmt))
    )
    with tempfile.NamedTemporaryFile() as filelist:
        subprocess.call(["ffmpeg", "-i", video_file, "-f", "segment",
                         "-segment_time", "1800", "-segment_list",
                         filelist.name, pattern])
        split_files = [filename.strip() for filename in filelist]
        
    split_files = [os.path.join(output_dir, filename)
                   for filename in split_files]
    
    return split_files
    
def mp4_to_audio_file(video_file, output_file):
    subprocess.call(["ffmpeg", "-i", video_file, output_file])
    return output_file
