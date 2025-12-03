import os
import sys
import glob
from scripts.whisper_gen import load_transcription_model, transcribe_with_model, unload_model

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def transcribe(input_folder='tmp', output_folder='subs'):
    if not os.path.exists(input_folder):
        print(f"Input folder {input_folder} does not exist.")
        return

    files = glob.glob(os.path.join(input_folder, "*_original_scale.mp4"))
    if not files:
        print("No files found to transcribe.")
        return

    model_name = os.getenv('WHISPER_MODEL_NAME', 'tiny')
    model, device = load_transcription_model(model_name)
    
    try:
        for input_file in files:
            transcribe_with_model(model, device, input_file, output_folder)
    finally:
        unload_model(model)