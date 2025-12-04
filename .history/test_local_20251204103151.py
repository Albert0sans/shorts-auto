import contextlib
import os
import shutil
import logging
import tempfile
from google import genai
from scripts.whisper_gen import generate_whisperx
from scripts import (
    create_viral_segments,
    cut_segments,
    transcribe_cuts,
    adjust_subtitles,
    burn_subtitles
)

@contextlib.contextmanager
def temporary_work_dir():
    prev_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        try:
            yield temp_dir
        finally:
            os.chdir(prev_cwd)

os.environ["GCLOUD_PROJECT"] = "studio-2517797099-c9afe"
os.environ["WHISPER_MODEL_NAME"] = "tiny"
os.environ["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "true"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    absolute_video_path = os.path.abspath(input_video_path)

    try:
        with temporary_work_dir() as temp_dir:
            folders = ['all', 'archive', 'tmp', 'final', 'subs', 'subs_ass', 'burned_sub']
            
            for d in folders:
                if os.path.exists(d):
                    shutil.rmtree(d)
                os.makedirs(d, exist_ok=True)
            
            logging.info(f"🚀 Starting local test with video: {absolute_video_path}")
            
            if not os.path.exists(absolute_video_path):
                logging.error(f"❌ Input file not found: {absolute_video_path}")
                return

            target_input = "tmp/input_video.mp4"
            shutil.copy2(absolute_video_path, target_input)

            logging.info("🎙️ Step 2: Generating initial full video transcription...")
            generate_whisperx(target_input, 'tmp')

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
                num_segments=2, 
                instructions=prompt,
                tempo_minimo=15,
                tempo_maximo=60,
                client=client,
            )

            if not viral_data or "segments" not in viral_data or not viral_data["segments"]:
                logging.error("❌ No viral segments found by AI.")
                return

            logging.info(f"✅ Found {len(viral_data['segments'])} segments.")

            logging.info("✂️ Step 4: Cutting segments...")
            cut_segments.cut(viral_data["segments"])

            logging.info("📝 Step 5: Transcribing individual cuts...")
            transcribe_cuts.transcribe(input_folder='tmp', output_folder='subs')

            logging.info("🎨 Step 6: Adjusting subtitle styles...")
            adjust_subtitles.adjust(
                STYLE_CONFIG['base_color'], STYLE_CONFIG['base_size'], STYLE_CONFIG['h_size'], 
                STYLE_CONFIG['highlight_color'], STYLE_CONFIG['palavras_por_bloco'], 
                STYLE_CONFIG['limite_gap'], STYLE_CONFIG['modo'], STYLE_CONFIG['posicao_vertical'], 
                STYLE_CONFIG['alinhamento'], STYLE_CONFIG['fonte'], STYLE_CONFIG['contorno'], 
                STYLE_CONFIG['cor_da_sombra'], STYLE_CONFIG['negrito'], 
                0, 0, 0, 1, 5, 1
            )

            logging.info("🔥 Step 7: Burning subtitles, cropping, and adding titles...")
            burn_subtitles.burn_with_title_and_channel(
                optional_header="", 
                segments=viral_data["segments"], 
                font_size=100, 
                channel_name="@local_test",
                aspect_ratio="9:16"
            )
            
            logging.info("✨ Test completed successfully!")
            
            final_output_dir = os.path.join(os.path.dirname(absolute_video_path), 'output_burned_sub')
            if os.path.exists(final_output_dir):
                shutil.rmtree(final_output_dir)
            shutil.copytree('burned_sub', final_output_dir)
            logging.info(f"📂 Output files copied to: {final_output_dir}")

    except Exception as e:
        logging.error(f"❌ Test failed with error: {e}", exc_info=True)

if __name__ == "__main__":
    SAMPLE_VIDEO_PATH = "test.mp4" 
    CUSTOM_PROMPT = "Find the funniest moments"
    
    if not os.path.exists(SAMPLE_VIDEO_PATH):
        print(f"Error: Please place a file named '{SAMPLE_VIDEO_PATH}' in this directory to run the test.")
    else:
        local_test(SAMPLE_VIDEO_PATH, prompt=CUSTOM_PROMPT)