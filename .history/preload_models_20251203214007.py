import whisperx
import gc
import os

def preload():
    print("--- Preloading Models for Cloud Run Persistence ---")
    
    device = "cpu"
    compute_type = "int8"


    transcription_models = ["tiny", "large-v3-turbo"]

    for model_name in transcription_models:
        print(f"Downloading Transcription Model: {model_name}...")
        try:
            whisperx.load_model(
                model_name, 
                device=device, 
                compute_type=compute_type
            )
            print(f"Successfully downloaded {model_name}")
        except Exception as e:
            print(f"Error downloading {model_name}: {e}")
        
        gc.collect()

    alignment_languages = ["en", "es"]
    
    print("Downloading Alignment Models (wav2vec2)...")
    for lang in alignment_languages:
        print(f"Downloading Alignment Model for language: {lang}...")
        try:
            whisperx.load_align_model(
                language_code=lang, 
                device=device
            )
            print(f"Successfully downloaded alignment model for {lang}")
        except Exception as e:
            print(f"Error downloading alignment model for {lang}: {e}")
        
        gc.collect()

    print("--- All Models Downloaded Successfully ---")

if __name__ == "__main__":
    preload()