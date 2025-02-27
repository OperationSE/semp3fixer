import subprocess 
import argparse as ap

from glob import iglob
from io import BytesIO
from os.path import splitext, basename, join, dirname, isdir
from os import makedirs

from mutagen.mp3 import MP3
from mutagen.id3 import COMM

from colorama import Fore, Style
from tqdm import tqdm


# Original author: sdardouchi for OperationSE
"""
A few notes are needed here:
The only output formats supported is MP3 since it's the most commonly supported format across all SE Walkman phones. 
(M4A is widely supported too but the metadata fix only works for MP3 files)

I'm not sure this will work with some formats listed in the script (ogg, wma, aac, opus)
but I'm pretty adamant it'll work with the rest of the formats.

The cover art is resized to 500x500 as the Walkman parsers generally don't support anything higher than that.
For some reason, Walkman 3.0 only supports the YUV420 pixel format, even though Walkman 2.0 parses YUV444 just fine.

The script assumes FFMPEG is in PATH, but you can specify the path to the executable with the --ffmpeg-path argument.

The metadata_fix function is here to remove all the useless tags that the Walkman 2.0 parser doesn't like
since it's the lowest common denominator between all Walkman versions, meaning that MP3s that work on it will work on all SE Walkman players.

The script will create the output folder structure as the input folder, so if your input folder is /home/user/Music
and you have a file in /path/to/input/folder/Linkin Park - Hybrid Theory/01 - Papercut.flac (could be any file format listed in the script really)
the output file will be in /path/to/output/folder/Linkin Park - Hybrid Theory/01 - Papercut.mp3
"""

def metadata_fix(mp3_file):
    mp3 = MP3(mp3_file)
     
    # Remove all comments and useless tags
    # Remove description on APIC tag (for some reason the parser breaks when there's one)
    for k,v in mp3.tags.items():
        if k.startswith("COMM") or k.startswith("TXXX") or k.startswith("WXXX"):
            mp3.pop(k)
        elif k.startswith("APIC"):
            v.desc = u'' 

    # The Walkman 2.0 parser BREAKS when there's no COMM tag, and the album cover doesn't show up
    mp3.tags.add(COMM(encoding=3,  text=u'SEMP3FIXED')) 
    mp3.save(mp3_file, v2_version=3)

def create_output_folder(output_folder, root_input_folder, matched_file):
    output_subfolder = output_folder + matched_file.replace(root_input_folder, "")
    output_subfolder = dirname(output_subfolder)
    makedirs(output_subfolder, exist_ok=True)
    return output_subfolder

def convert_file(input_file, output_folder, ffmpeg_path):
    flags = "-hide_banner -loglevel error"
    output_filename = splitext(basename(input_file))[0] + ".mp3"
    output_file = join(output_folder, output_filename)
    command = f"{ffmpeg_path} {flags} -i \"{input_file}\" -pix_fmt yuv420p -vf scale=500:500 -map 0:0 -c:a mp3 -b:a 192k -map 0:1 -map_metadata 0 -c:v mjpeg \"{output_file}\""
    subprocess.run(command, shell=True)
    return output_file

def main():
    parser = ap.ArgumentParser(description="Converts any audio files to MP3 and fixes metadata for Sony Ericsson phones")
    parser.add_argument("-i", "--input_folder", help="Folder containing the audio files", required=True)
    parser.add_argument("-o", "--output_folder", help="Folder where the converted files will be saved", required=True)
    parser.add_argument("--ffmpeg-path", help="Path to the ffmpeg executable", default="ffmpeg")
    args = parser.parse_args()

    if not isdir(args.input_folder):
        print(Fore.RED + "[!] Invalid input folder" + Fore.RESET)
        exit(1)

    types = [".mp3", ".flac", ".ogg", ".wav", ".m4a", ".wma", ".aac", ".opus"]
    files = [f for t in types for f in iglob(args.input_folder + "/**/*" + t, recursive=True)]

    print(Fore.GREEN + f"[✓] Found {len(files)} audio files to convert" + Fore.RESET)
    print(Fore.LIGHTGREEN_EX + f"[i] Output folder: {args.output_folder}")
    print(Fore.LIGHTGREEN_EX + f"[i] Starting conversion" + Fore.RESET)

    try: 
        for file in tqdm(files, desc="Converting files", unit="file"):
            output_folder = create_output_folder(args.output_folder, args.input_folder, file)
            output_file = convert_file(file, output_folder, args.ffmpeg_path)
            metadata_fix(output_file)
    except KeyboardInterrupt:
        print(Fore.RED + "\n[!] Conversion interrupted" + Fore.RESET)
        exit(1)

if __name__ == "__main__": main()