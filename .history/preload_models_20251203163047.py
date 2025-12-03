import whisperx
import torch
import gc
from faster_whisper import download_model
from omegaconf import ListConfig, DictConfig
from huggingface_hub.utils import _runtime
_runtime._is_google_colab = False
print("Downloading WhisperX tiny model...")



model_dir = download_model("tiny")
print(f"Transcription model downloaded to: {model_dir}")

torch.serialization.add_safe_globals([ListConfig, DictConfig])

print("Downloading Alignment models (wav2vec2)...")
for lang in ["en", "es"]:
    print(f"Downloading Alignment model for {lang}...")
    whisperx.load_align_model(language_code=lang, device="cpu")

    
    gc.collect()

print("Models downloaded successfully.")

print("testing model transcribe")



