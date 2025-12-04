




import os
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "0"
os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_DEBUG"] = "1"

import logging
import sys

import gc
import time
import threading
import shutil
import torch
import whisperx
from faster_whisper import download_model
from omegaconf import ListConfig, DictConfig
from huggingface_hub.utils import _runtime


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

hf_home = os.environ.get("HF_HOME", "/app/cache/huggingface")
torch_home = os.environ.get("TORCH_HOME", "/app/cache/torch")
# Configure logging to output to stdout immediately

import shutil

_runtime._is_google_colab = False
torch.serialization.add_safe_globals([ListConfig, DictConfig])

def preload():
    logger.info("--- Starting Model Preload for Cloud Run ---")
    
    # 1. Download Transcription Models
    transcription_models = ["tiny", "large-v3-turbo"]
    
    for model_name in transcription_models:
        logger.info(f"Starting download for transcription model: {model_name}")
        
        
        try:
            # Download the model files
            model_path = download_model(model_name)
            logger.info(f"Successfully downloaded {model_name} to {model_path}")
        except Exception as e:
            logger.error(f"CRITICAL ERROR downloading {model_name}: {e}")
            raise e

        
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

    logger.info("--- Preload Script Finished Successfully ---")

if __name__ == "__main__":
    preload()