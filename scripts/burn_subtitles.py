import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
def check_nvenc_support():
        try:
            result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
            return "h264_nvenc" in result.stdout
        except subprocess.CalledProcessError:
            return False


        
def burn():
    if not check_nvenc_support():
            print("NVENC is not supported on this system. Falling back to libx264.")
            video_codec = "libx264"
    else:
            video_codec = "h264_nvenc"
    # Caminhos das pastas
    subs_folder = 'subs_ass'
    videos_folder = 'final'
    output_folder = 'burned_sub' 

    # Cria a pasta de saída se não existir
    os.makedirs(output_folder, exist_ok=True)

    # Itera sobre os arquivos de vídeo na pasta final
    for video_file in os.listdir(videos_folder):
        if video_file.endswith(('.mp4 .mkv .avi')):  # Formatos suportados
            video_name = os.path.splitext(video_file)[0]

            # Define o caminho para a legenda correspondente
            subtitle_file = os.path.join(subs_folder, f"{video_name}.ass")

            # Verifica se a legenda existe
            if os.path.exists(subtitle_file):
                # Define o caminho de saída para o vídeo com legendas
                output_file = os.path.join(output_folder, f"{video_name}_subtitled.mp4")

                # Ajuste no caminho da legenda para FFmpeg
                subtitle_file_ffmpeg = subtitle_file.replace('\\ /')

                # Comando FFmpeg para adicionar as legendas
                command = [
                    'ffmpeg',
                    '-i', os.path.join(videos_folder, video_file),  
                    '-vf', f"subtitles='{subtitle_file_ffmpeg}'",  
                    '-c:v', video_codec,
                    '-preset superfast',  
                    '-b:v 5M', 
                    '-c:a copy',  
                    output_file
                ]

                # Log dos caminhos e do comando
                print(f"Processando vídeo: {video_file}")
                print(f"Caminho da legenda: {subtitle_file}")
                print(f"Caminho de saída: {output_file}")
                print(f"Comando: {' '.join(command)}")

                # Executa o comando
                try:
                    subprocess.run(command, check=True)
                    print(f"Processado: {output_file}")
                except subprocess.CalledProcessError as e:
                    print(f"Erro ao processar {video_name}: {e}")
            else:
                print(f"Legenda não encontrada para: {video_name}")
import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def check_nvenc_support():
    """Checks if the h264_nvenc encoder is available."""
    try:
        # Try to run ffmpeg with -encoders and check the output
        result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, check=False)
        return "h264_nvenc" in result.stdout
    except FileNotFoundError:
        # ffmpeg not found
        print("FFmpeg not found. Please ensure it is installed and in your PATH.")
        return False
    except Exception:
        # Other subprocess errors
        return False

# Retaining original 'burn' function just in case, though it's not used in the example
def burn():
    # ... (original burn function code - left out for brevity, assuming you have it)
    pass 

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
    
    # New parameters for the channel name
    channel_name="@dailytoon",
    channel_font_file='emojione.ttf', # Typically a different font for contrast
    channel_font_size=32,          # Smaller font size
    channel_font_color='0xAAAAAA', # Light gray for a "faded" effect (hex RRGGBB)
    channel_y_offset=150            # Vertical offset from the main title's y_pos
):
    """
    Processes videos, adding ASS subtitles, a main title, and a channel name below it.

    Args:
        ... (Arguments for main title)
        channel_name (str): The channel name to display.
        channel_font_file (str): The path to the font file for the channel name.
        channel_font_size (int): The font size for the channel name.
        channel_font_color (str): The color for the channel name (FFmpeg hex 0xRRGGBB).
        channel_y_offset (int): Vertical distance in pixels from the title's Y position.
    """
    
    # 1. Codec Configuration
    if not check_nvenc_support():
        print("NVENC not supported. Falling back to libx264.")
        video_codec = "libx264"
        preset = "superfast"
    else:
        print("NVENC supported. Using h264_nvenc.")
        video_codec = "h264_nvenc"
        preset = "p5"

    # 2. Folder Configuration
    subs_folder = 'subs_ass'
    videos_folder = 'final'
    output_folder = 'burned_sub' 

    os.makedirs(output_folder, exist_ok=True)
    
    for idx,segment in enumerate(segments):
            video_file=f"final-output{str(idx).zfill(3)}_processed.mp4"

            video_name = os.path.splitext(video_file)[0]
            subtitle_file = os.path.join(subs_folder, f"{video_name}.ass")
            output_file = os.path.join(output_folder, f"{video_name}.mp4")
            if not os.path.exists(output_file):
                short_title=segment["title"]
                print(subtitle_file)
                subtitle_file_ffmpeg = subtitle_file.replace('\\','/')
                
                short_title=short_title.replace(":",'')
                short_title = short_title.replace("'", "''")
                
                # 4.1. Main Title Filter
                drawtext_optional_header_filter = (
                    f"drawtext="
                    f"text='{optional_header}':"
                    f"fontfile='{font_file}':"
                    f"fontsize={font_size}:"
                    f"fontcolor={font_color}:"
                    f"x={x_pos}:"
                    f"y={y_pos_opt}:"
                    f"shadowcolor={shadow_color}:"
                    f"shadowx={shadow_offset}:"
                    f"shadowy={shadow_offset}"
                )
                drawtext_short_title_filter = (
                    f"drawtext="
                    f"text='{short_title}':"
                    f"fontfile='{font_file}':"
                    f"fontsize=70:"
                    f"fontcolor={font_color}:"
                    f"x={x_pos}:"
                    f"y={y_pos} + {font_size}:"
                    f"shadowcolor={shadow_color}:"
                    f"shadowx={shadow_offset}:"
                    f"shadowy={shadow_offset}"
                )


                
                
                drawtext_channel_filter = (
                    f"drawtext="
                    f"text='{channel_name}':"
                    f"fontfile='{channel_font_file}':"
                    f"fontsize={channel_font_size}:"
                    f"fontcolor={channel_font_color}:"
                    f"x=(w-text_w)/2:" # Center the channel name text
                    f"y={y_pos} + {channel_y_offset}:" # Place it below the main title
                    f"shadowcolor={shadow_color}:"
                    f"shadowx={shadow_offset}:"
                    f"shadowy={shadow_offset}"
                )

                # 5. VIDEO FILTER GRAPH CREATION (-vf)
                # Chained filters: Title -> Channel Name -> Subtitles
                video_filter_graph = (
                     f"{drawtext_short_title_filter},"
                    f"{drawtext_optional_header_filter},"
                    f"{drawtext_channel_filter},"
                    f"subtitles='{subtitle_file_ffmpeg}'"
                )

                # 6. FFmpeg Command
                command = [
                    'ffmpeg',
                    '-i', os.path.join(videos_folder, video_file),  
                    '-vf', video_filter_graph, # The new, multi-part filter graph
                    '-c:v', video_codec,
                    '-preset', preset,  
                   '-b:v', '5M', 
                    '-c:a', 'copy', 
                    '-y', 
                    output_file
                ]

                # Log
                print(f"\nProcessing video with TITLE, CHANNEL, and Subtitles: {video_file}")
                print(f"Subtitle path: {subtitle_file}")
                # Print the full command for debugging, removing the long -vf string for readability
                print(f"Command (excerpt): ffmpeg -i ... -vf [drawtext,drawtext,subtitles] ... {output_file}")
                
                # Execute
                try:
                    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                    print(f"SUCCESS: {output_file}")
                except subprocess.CalledProcessError as e:
                    print(f"ERROR processing {video_name}. Check font paths or FFmpeg output {e.output}")
                    raise
            else:
                print(f"skipping: {video_name}")

