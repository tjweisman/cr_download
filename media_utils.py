import os
import re
import tempfile

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
        filelist = tempfile.NamedTemporaryFile()
        subprocess.call(["ffmpeg", "-i", video_file, "-f", "segment",
                         "-segment_time", "1800", "-segment_list",
                         filelist.name, output_pattern])
        
        split_files = [filename for filename in filelist]
        filelist.close()
        return split_files
    else:
        subprocess.call(["ffmpeg", "-i", video_file, output_file])
        return output_file
