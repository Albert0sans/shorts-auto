import logging
import sys
import os
import gc
import time
import threading
import torch
import whisperx
from faster_whisper import download_model
from omegaconf import ListConfig, DictConfig
from huggingface_hub.utils import _runtime
hf_home = os.environ.get("HF_HOME", "/app/cache/huggingface")
torch_home = os.environ.get("TORCH_HOME", "/app/cache/torch")
# Configure logging to output to stdout immediately
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

_runtime._is_google_colab = False
torch.serialization.add_safe_globals([ListConfig, DictConfig])

def log_progress(stop_event, model_name):
    """Background thread to log progress every 10 seconds."""
    start_time = time.time()
    while not stop_event.is_set():
        time.sleep(120)
        if not stop_event.is_set():
            elapsed = int(time.time() - start_time)
            logger.info(f"Downloading {model_name}... ({elapsed}s elapsed)")
            log_directory_contents("HuggingFace Cache", hf_home)
            log_directory_contents("Torch Cache", torch_home)
def log_directory_contents(path_name, path):
    """Logs files and sizes in the given directory."""
    if not path or not os.path.exists(path):
        logger.warning(f"Directory for {path_name} does not exist: {path}")
        return

    logger.info(f"--- Listing contents of {path_name} ({path}) ---")
    total_size = 0
    file_count = 0
    
    for root, _, files in os.walk(path):
        for name in files:
            filepath = os.path.join(root, name)
            try:
                size = os.path.getsize(filepath)
                total_size += size
                file_count += 1
                # Convert to MB
                size_mb = size / (1024 * 1024)
                # Print relative path for cleaner logs
                rel_path = os.path.relpath(filepath, path)
                logger.info(f"[{size_mb:.2f} MB] {rel_path}")
            except Exception as e:
                logger.error(f"Error reading {filepath}: {e}")

    total_mb = total_size / (1024 * 1024)
    total_gb = total_mb / 1024
    logger.info(f"--- Summary for {path_name}: {file_count} files, {total_mb:.2f} MB ({total_gb:.2f} GB) ---")

def preload():
    logger.info("--- Starting Model Preload for Cloud Run ---")
    
    # 1. Download Transcription Models
    transcription_models = ["tiny", "large-v3-turbo"]
    
    for model_name in transcription_models:
        logger.info(f"Starting download for transcription model: {model_name}")
        
        stop_event = threading.Event()
        progress_thread = threading.Thread(target=log_progress, args=(stop_event, model_name))
        progress_thread.start()
        
        try:
            # Download the model files
            model_path = download_model(model_name)
            logger.info(f"Successfully downloaded {model_name} to {model_path}")
        except Exception as e:
            logger.error(f"CRITICAL ERROR downloading {model_name}: {e}")
            raise e
        finally:
            stop_event.set()
            progress_thread.join()
        
        gc.collect()


    # 3. Download Alignment Models
    alignment_languages = ["en", "es"]
    logger.info(f"Downloading alignment models for: {alignment_languages}")
    
    for lang in alignment_languages:
        try:
            whisperx.load_align_model(language_code=lang, device="cpu")
            logger.info(f"Successfully downloaded alignment model for {lang}")
        except Exception as e:
            logger.error(f"Error downloading alignment for {lang}: {e}")
        gc.collect()

    logger.info("--- Download Phase Complete. Verifying Cache ---")
    
    # 4. List Cached Files

    
    log_directory_contents("HuggingFace Cache", hf_home)
    log_directory_contents("Torch Cache", torch_home)

    logger.info("--- Preload Script Finished Successfully ---")

if __name__ == "__main__":
    preload()