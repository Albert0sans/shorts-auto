import subprocess
import os
from concurrent.futures import ThreadPoolExecutor

def cut(segments):
    def check_nvenc_support():
        try:
            result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
            return "h264_nvenc" in result.stdout
        except subprocess.CalledProcessError:
            return False

    def process_segment(args):
        i, segment, video_codec = args
        input_file = "tmp/input_video.mp4"
        start_time = segment["start_time"]
        end_time = segment["end_time"]
        duration = (end_time - start_time) / 1000
        output_file = f"tmp/output{str(i).zfill(3)}_original_scale.mp4"
        
        if os.path.exists(output_file):
            return

        command = [
            "ffmpeg", "-y",
            "-ss", str(int(start_time)/1000),
            "-i", input_file,
            "-t", str(duration),
            "-c:v", video_codec
        ]

        if video_codec == "h264_nvenc":
            command.extend(["-preset", "p1", "-b:v", "5M"])
        else:
            command.extend(["-preset", "ultrafast", "-crf", "23"])

        command.extend(["-c:a", "aac", "-b:a", "128k", output_file])

        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"Generated segment {i}")
        except subprocess.CalledProcessError as e:
            print(f"Error generating segment {i}: {e}")

    if not os.path.exists("tmp/input_video.mp4"):
        print("Input file not found.")
        return

    video_codec = "h264_nvenc" if check_nvenc_support() else "libx264"
    
    tasks = [(i, seg, video_codec) for i, seg in enumerate(segments)]
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(process_segment, tasks)