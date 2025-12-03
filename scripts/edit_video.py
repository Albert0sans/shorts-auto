import os
import subprocess


def editv2(aspectRatio="9:16"):
    """
    Processes videos in the 'tmp/' directory to a specific aspect ratio
    and saves them to the 'final/' directory.
    
    Args:
        aspectRatio (str): Target aspect ratio in "W:H" format (e.g., "9:16", "16:9").
    """

    def check_nvenc_support():
        try:
            result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, check=True)
            return "h264_nvenc" in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
            
    # Determine codec based on hardware support
    if not check_nvenc_support():
        video_codec = "libx264"
        codec_options = "-preset fast -crf 23" 
    else:
        video_codec = "h264_nvenc"
        codec_options = "-preset fast -b:v 2M"

    def process_video_with_ffmpeg(input_file, final_output, video_codec, codec_options, aspect_ratio_str):
        
        # Parse aspect ratio to determine dimensions
        try:
            ar_w, ar_h = map(int, aspect_ratio_str.split(':'))
        except ValueError:
            raise ValueError(f"Invalid aspect ratio format: {aspect_ratio_str}. Use format like '9:16'.")

        # Set a base dimension to calculate the other (e.g., base width 1080 for vertical/square)
        # You can adjust this logic based on your preferred resolution standards.
        if ar_w > ar_h: # Landscape (e.g., 16:9)
            output_h = 1080
            output_w = int(output_h * (ar_w / ar_h))
        else: # Portrait (e.g., 9:16) or Square
            output_w = 1080
            output_h = int(output_w * (ar_h / ar_w))

        # Ensure dimensions are divisible by 2 for most codecs
        if output_w % 2 != 0: output_w += 1
        if output_h % 2 != 0: output_h += 1

        bg_filter = (
            f"[0:v]scale={output_w}:{output_h}:force_original_aspect_ratio=increase,"
            f"crop={output_w}:{output_h},"
            f"boxblur=luma_radius=150:luma_power=3[bg];"
        )

        fg_filter = (
            f"[0:v]scale={output_w}:{output_h}:force_original_aspect_ratio=decrease[fg];"
        )
        
        overlay_filter = f"[bg][fg]overlay=(W-w)/2:(H-h)/2[out]"

        complex_filters = f"{bg_filter}{fg_filter}{overlay_filter}"

        command = [
            "ffmpeg", "-y", 
            "-i", input_file,
            "-filter_complex", complex_filters,
            "-map", "[out]",
            "-map", "0:a?",
            "-c:v", video_codec, 
            *codec_options.split(),
            "-c:a", "aac", 
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            final_output
        ]
        
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise Exception(f"FFmpeg processing failed for {input_file}. Error: {e.stderr}")
        except FileNotFoundError:
            raise FileNotFoundError("FFmpeg executable not found. Please ensure it is installed and in your PATH.")


    final_dir = "final/"
    os.makedirs(final_dir, exist_ok=True)
    index = 0
    
    while True:
        input_file = f'tmp/output{str(index).zfill(3)}_original_scale.mp4'
        # output_file is unused but kept for reference if logic changes later
        output_file = f"tmp/output{str(index).zfill(3)}_processed.mp4" 
        final_output = os.path.join(final_dir, f"final-output{str(index).zfill(3)}_processed.mp4")
        
        if not os.path.exists(input_file):
            print(f"Processing complete. {index} files checked.")
            break
            
        if os.path.exists(final_output):
            print(f"Skipping existing file: {final_output}")
            index += 1
            continue
            
        try:
            print(f"Processing: {final_output} with aspect ratio {aspectRatio}")
            process_video_with_ffmpeg(input_file, final_output, video_codec, codec_options, aspectRatio)
            print(f"Final file generated at: {final_output}")
        except Exception as e:
            print(f"Error processing video {input_file}: {e}")
        
        index += 1