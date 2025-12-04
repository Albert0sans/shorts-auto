import os
import shutil
import logging
from google import genai
from scripts.whisper_gen import generate_whisperx
from scripts import (
    create_viral_segments,
    cut_segments,
    transcribe_cuts,
    adjust_subtitles,
    burn_subtitles
)

# --- ENVIRONMENT VARIABLES CONFIGURATION ---
# Set these before any other logic runs
os.environ["GCLOUD_PROJECT"] = "studio-2517797099-c9afe"  # REQUIRED: Replace with your actual Project ID
os.environ["WHISPER_MODEL_NAME"] = "tiny"                         # OPTIONAL: 'tiny', 'base', 'small', 'medium', 'large', 'large-v3-turbo'
os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "true"
# If you need explicit credentials (instead of 'gcloud auth application-default login'):
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/your/service-account-key.json" 

# Configure logging to see progress
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Subtitle Style Configuration
STYLE_CONFIG = {
    'base_color': '&HFFFFFF&',
    'highlight_color': '&H00FFFF&',
    'base_size': 12,
    'h_size': 14,
    'contorno': '&H000000&',
    'cor_da_sombra': '&H000000&',
    'modo': "highlight",
    'fonte': "Arial",
    'alinhamento': 2,
    'posicao_vertical': 60,
    'palavras_por_bloco': 3,
    'limite_gap': 0.2,
    'negrito': 1
}

def local_test(input_video_path, prompt=None):
    """
    Runs the shorts generation pipeline locally.
    """
    # Define working directories
    folders = ['all', 'archive', 'tmp', 'final', 'subs', 'subs_ass', 'burned_sub']
    
    # Clean and recreate directories
    for d in folders:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)

    try:
        logging.info(f"🚀 Starting local test with video: {input_video_path}")
        
        # 1. Prepare Input
        if not os.path.exists(input_video_path):
            logging.error(f"❌ Input file not found: {input_video_path}")
            return

        target_input = "tmp/input_video.mp4"
        shutil.copy2(input_video_path, target_input)

        # 2. Transcription (Full Video)
        logging.info("🎙️ Step 2: Generating initial full video transcription...")
        generate_whisperx(target_input, 'tmp')

        # 3. Viral Segments Analysis
        logging.info("🧠 Step 3: Identifying viral segments with Gemini...")
        
        project_id = os.environ.get("GCLOUD_PROJECT")
        if not project_id or project_id == "your-google-cloud-project-id":
             logging.warning("⚠️ GCLOUD_PROJECT not correctly set. Please update the env var at the top of the script.")
        
        location = "us-central1"
        client = None
        try:
             client = genai.Client(vertexai=True, project=project_id, location=location)
        except Exception as e:
            logging.error(f"❌ GenAI Client init failed: {e}. Check your Google Cloud credentials.")
            return

        viral_data = create_viral_segments.create_viral_segments(
            num_segments=2, # Generating 2 clips for the test
            instructions=prompt,
            tempo_minimo=15,
            tempo_maximo=60,
            client=client,
        )

        if not viral_data or "segments" not in viral_data or not viral_data["segments"]:
            logging.error("❌ No viral segments found by AI.")
            return

        logging.info(f"✅ Found {len(viral_data['segments'])} segments.")

        # 4. Cut Segments
        logging.info("✂️ Step 4: Cutting segments...")
        cut_segments.cut(viral_data["segments"])

        # 5. Transcribe Cuts
        logging.info("📝 Step 5: Transcribing individual cuts...")
        transcribe_cuts.transcribe(input_folder='tmp', output_folder='subs')

        # 6. Adjust Subtitles (Convert to ASS)
        logging.info("🎨 Step 6: Adjusting subtitle styles...")
        adjust_subtitles.adjust(
            STYLE_CONFIG['base_color'], STYLE_CONFIG['base_size'], STYLE_CONFIG['h_size'], 
            STYLE_CONFIG['highlight_color'], STYLE_CONFIG['palavras_por_bloco'], 
            STYLE_CONFIG['limite_gap'], STYLE_CONFIG['modo'], STYLE_CONFIG['posicao_vertical'], 
            STYLE_CONFIG['alinhamento'], STYLE_CONFIG['fonte'], STYLE_CONFIG['contorno'], 
            STYLE_CONFIG['cor_da_sombra'], STYLE_CONFIG['negrito'], 
            0, 0, 0, 1, 5, 1
        )

        # 7. Burn Subtitles & Process Video
        logging.info("🔥 Step 7: Burning subtitles, cropping, and adding titles...")
        burn_subtitles.burn_with_title_and_channel(
            optional_header="", 
            segments=viral_data["segments"], 
            font_size=100, 
            channel_name="@local_test",
            aspect_ratio="9:16"
        )
        
        logging.info("✨ Test completed successfully!")
        logging.info(f"📂 Output files are located in: {os.path.abspath('burned_sub')}")

    except Exception as e:
        logging.error(f"❌ Test failed with error: {e}", exc_info=True)

if __name__ == "__main__":
    # --- CONFIGURATION ---
    # Change this to the path of your local mp4 file
    SAMPLE_VIDEO_PATH = "test.mp4" 
    CUSTOM_PROMPT = "Find the funniest moments"
    
    # --- EXECUTION ---
    if not os.path.exists(SAMPLE_VIDEO_PATH):
        print(f"Error: Please place a file named '{SAMPLE_VIDEO_PATH}' in this directory to run the test.")
    else:
        local_test(SAMPLE_VIDEO_PATH, prompt=CUSTOM_PROMPT)