import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def check_nvenc_support():
    try:
        result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, check=False)
        return "h264_nvenc" in result.stdout
    except Exception:
        return False

def burn_with_title_and_channel(
    optional_header="My Title", 
    segments=[],
    font_file='Arial-Bold.ttf', 
    font_size=150, 
    font_color='white', 
    x_pos='(w-text_w)/2', 
    y_pos='(h-text_h)/5', 
    y_pos_opt='(h-text_h)/6',
    shadow_color='black', 
    shadow_offset=2,
    channel_name="@dailytoon",
    channel_font_file='emojione.ttf', 
    channel_font_size=32,          
    channel_font_color='0xAAAAAA', 
    channel_y_offset=150,
    aspect_ratio="9:16"
):
    video_codec = "h264_nvenc" if check_nvenc_support() else "libx264"
    preset = "p5" if video_codec == "h264_nvenc" else "superfast"

    subs_folder = 'subs_ass'
    input_folder = 'tmp'
    output_folder = 'burned_sub' 
    os.makedirs(output_folder, exist_ok=True)

    try:
        ar_w, ar_h = map(int, aspect_ratio.split(':'))
    except ValueError:
        ar_w, ar_h = 9, 16

    def process_video(idx, segment):
        # Input is now the cut segment in tmp
        video_file_name = f"output{str(idx).zfill(3)}_original_scale.mp4"
        input_path = os.path.join(input_folder, video_file_name)
        
        # Output filename expected by main.py
        final_output_name = f"final-output{str(idx).zfill(3)}_processed.mp4"
        output_file = os.path.join(output_folder, final_output_name)
        
        # Ass filename matches the outputXXX naming from transcribe_cuts
        subtitle_file = os.path.join(subs_folder, f"output{str(idx).zfill(3)}_original_scale.ass")

        if not os.path.exists(input_path):
            print(f"Input file missing: {input_path}")
            return

        if os.path.exists(output_file):
            return

        # Calculate dimensions
        if ar_w > ar_h: 
            output_h = 1080
            output_w = int(output_h * (ar_w / ar_h))
        else: 
            output_w = 1080
            output_h = int(output_w * (ar_h / ar_w))
            
        if output_w % 2 != 0: output_w += 1
        if output_h % 2 != 0: output_h += 1

        # Build Filters
        bg_filter = f"[0:v]scale={output_w}:{output_h}:force_original_aspect_ratio=increase,crop={output_w}:{output_h},boxblur=luma_radius=150:luma_power=3[bg];"
        fg_filter = f"[0:v]scale={output_w}:{output_h}:force_original_aspect_ratio=decrease[fg];"
        overlay_filter = f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v_base]"

        subtitle_filter = ""
        if os.path.exists(subtitle_file):
            subtitle_file_ffmpeg = subtitle_file.replace('\\', '/')
            subtitle_filter = f",subtitles='{subtitle_file_ffmpeg}'"

        short_title = segment.get("title", "").replace(":", "").replace("'", "''")
        
        drawtext_filters = (
            f",drawtext=text='{short_title}':fontfile='{font_file}':fontsize=70:fontcolor={font_color}:"
            f"x={x_pos}:y={y_pos} + {font_size}:shadowcolor={shadow_color}:shadowx={shadow_offset}:shadowy={shadow_offset},"
            f"drawtext=text='{optional_header}':fontfile='{font_file}':fontsize={font_size}:fontcolor={font_color}:"
            f"x={x_pos}:y={y_pos_opt}:shadowcolor={shadow_color}:shadowx={shadow_offset}:shadowy={shadow_offset},"
            f"drawtext=text='{channel_name}':fontfile='{channel_font_file}':fontsize={channel_font_size}:fontcolor={channel_font_color}:"
            f"x=(w-text_w)/2:y={y_pos} + {channel_y_offset}:shadowcolor={shadow_color}:shadowx={shadow_offset}:shadowy={shadow_offset}"
        )

        full_filter = f"{bg_filter}{fg_filter}{overlay_filter}[v_base];[v_base]null{drawtext_filters}{subtitle_filter}[v_out]"

        command = [
            'ffmpeg', '-y',
            '-i', input_path,
            '-filter_complex', full_filter,
            '-map', '[v_out]',
            '-map', '0:a?',
            '-c:v', video_codec,
            '-preset', preset,
            '-b:v', '5M',
            '-c:a', 'aac',
            '-b:a', '192k',
            output_file
        ]

        try:
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            print(f"Processed: {output_file}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to process {input_path}:{e}")

    with ThreadPoolExecutor(max_workers=2) as executor:
        for idx, segment in enumerate(segments):
            executor.submit(process_video, idx, segment)