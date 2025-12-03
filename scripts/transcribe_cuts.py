import os
import subprocess
import sys

from scripts.whisper_gen import generate_whisperx

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def transcribe():
    

    # Define o diretório de entrada e o diretório de saída
    input_folder = 'final/'
    output_folder = 'subs/'
    # Itera sobre todos os arquivos na pasta de entrada
    for filename in os.listdir(input_folder):
        if filename.endswith('.mp4'):  # Filtra apenas arquivos .mp4
            input_file = os.path.join(input_folder, filename)
            generate_whisperx(input_file, output_folder)



def get_audio(input_file):
    """
    Extracts audio from a media file using ffmpeg, converts it to a 16kHz mono WAV file,
    and returns the path to the output file.

    Args:
        input_file (str): The path to the input audio or video file.

    Returns:
        str: The path to the generated .wav file.
        
    Raises:
        FileNotFoundError: If ffmpeg is not installed or not in the system's PATH.
        subprocess.CalledProcessError: If the ffmpeg command fails for any reason.
    """
    # Create the output filename by replacing the original extension with .wav
    base_name = os.path.splitext(input_file)[0]
    output_file = f"{base_name}.wav"

    # Construct the ffmpeg command as a list of arguments
    command = [
        'ffmpeg',
        '-i', input_file,     # Input file
        '-vn',                # Disable video
        '-acodec', 'pcm_s16le', # Set audio codec to 16-bit PCM (standard for WAV)
        '-ar', '16000',       # Set audio sample rate to 16kHz
        '-ac', '1',           # Set to 1 audio channel (mono)
        '-y',                 # Overwrite output file if it exists
        output_file
    ]

    try:
        # Execute the command, hiding ffmpeg's console output
        subprocess.run(
            command, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        print(f"✅ Audio extracted successfully to: {output_file}")
        return output_file
    except FileNotFoundError:
        # This error occurs if ffmpeg is not installed or not in the system PATH
        raise FileNotFoundError("ffmpeg not found. Please install ffmpeg and add it to your system's PATH.")
    except subprocess.CalledProcessError as e:
        # This error occurs if ffmpeg fails for other reasons (e.g., corrupt input file)
        print("❌ An error occurred during audio extraction.")
        # Print the error message from ffmpeg for debugging
        print(f"ffmpeg error:\n{e.stderr.decode()}")
        raise

