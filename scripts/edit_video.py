import os
import subprocess
import cv2 
import numpy as np # Retained, though not strictly needed for the FFmpeg approach, in case other parts of your code rely on it.

def editv2():

    def check_nvenc_support():
        try:
            result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, check=True)
            return "h264_nvenc" in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
            
    if not check_nvenc_support():
        video_codec = "libx264"
        codec_options = "-preset fast -crf 23" 
    else:
        video_codec = "h264_nvenc"
        codec_options = "-preset fast -b:v 2M"

    def process_video_with_ffmpeg(input_file, final_output, video_codec, codec_options):
        
        output_w = 1080
        output_h = 1920

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
            # Re-raise the error if debugging is not the user's focus
            raise Exception(f"FFmpeg processing failed for {input_file}. Error: {e.stderr}")
        except FileNotFoundError:
            raise FileNotFoundError("FFmpeg executable not found. Please ensure it is installed and in your PATH.")


    final_dir = "final/"
    os.makedirs(final_dir, exist_ok=True)
    index = 0
    
    while True:
        input_file = f'tmp/output{str(index).zfill(3)}_original_scale.mp4'
        output_file = f"tmp/output{str(index).zfill(3)}_processed.mp4" # Intermediate file name (unused, but kept for logic)
        final_output = os.path.join(final_dir, f"final-output{str(index).zfill(3)}_processed.mp4")
        print(final_output)
        if not os.path.exists(input_file):
            print(f"Processamento completo. {index} arquivos verificados.")
            break
            
        if os.path.exists(final_output):
            index += 1
            continue
            
        try:
            process_video_with_ffmpeg(input_file, final_output, video_codec, codec_options)
            print(f"Arquivo final gerado em: {final_output}")
        except Exception as e:
            print(f"Erro ao processar o vídeo {input_file}: {e}")
        
        index += 1

if __name__ == "__main__":
    os.makedirs('tmp', exist_ok=True)
    # The original structure of the code is simplified since it no longer uses cv2
    # for frame processing. The generate_short function is replaced by the FFmpeg
    # call directly in the loop. The resize_with_padding function is fully removed.
    editv2()