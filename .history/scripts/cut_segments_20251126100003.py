import subprocess
import subprocess
import os
    
def cut(segments):

    def check_nvenc_support():
        try:
            result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
            return "h264_nvenc" in result.stdout
        except subprocess.CalledProcessError:
            return False

    def generate_segments(response):
        if not check_nvenc_support():
            print("NVENC is not supported on this system. Falling back to libx264.")
            video_codec = "libx264"
        else:
            video_codec = "h264_nvenc"

        input_file = "tmp/input_video.mp4"
        if not os.path.exists(input_file):
            print(f"Input file not found: {input_file}")
            return

        segments = response
        for i, segment in enumerate(segments):
            print(segment)
            start_time = segment["start_time"]
            end_time = segment["end_time"]
            duration = (end_time-start_time) /1000 # Utiliza a duração para calcular o corte
            print(duration)
            output_file = f"tmp/output{str(i).zfill(3)}_original_scale.mp4"
            if  os.path.exists(output_file):
                continue
            # Comando ffmpeg ajustado para usar -ss antes de -i e -t para a duração
            command = [
                "ffmpeg",
                "-y",
                "-ss", str(int(start_time)/1000),          # Corte antes de decodificar
                "-i", input_file,
                "-t", str(duration),        # Define a duração do segmento
                "-c:v", video_codec
            ]

            if video_codec == "h264_nvenc":
                command.extend([
                    "-preset", "p1",  # Fast encoding preset for NVENC
                    "-b:v", "5M",     # Set bitrate instead of CRF for NVENC
                ])
            else:
                command.extend([
                    "-preset", "ultrafast",
                    "-crf", "23"
                ])

            command.extend([
                "-c:a", "aac",
                "-b:a", "128k",
                f"{output_file}"
            ])

            print(f"Processing segment {i+1}/{len(segments)}")
            print(f"Start time: {start_time}, Duration: {duration} seconds")
            print(f"Executing command: {' '.join(command)}")

            # Executando o comando
            try:
                result = subprocess.run(command, check=True, capture_output=True, text=True)
                print(f"Command output: {result.stdout}")
                #print(f"Command error output: {result.stderr}")
            except subprocess.CalledProcessError as e:
                print(f"Error executing ffmpeg: {e}")
                #print(f"Error output: {e.stderr}")
                continue

            if os.path.exists(f"{output_file}"):
                file_size = os.path.getsize(f"{output_file}")
                print(f"Generated segment: {output_file}, Size: {file_size} bytes")
            else:
                print(f"Failed to generate segment: {output_file}")

            print("\n" + "="*50 + "\n")
    generate_segments(segments)
