import os
import shutil
import uuid
from hashlib import sha1
import functions_framework
from flask import jsonify
import firebase_admin
from firebase_admin import credentials, storage, auth, firestore

if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'storageBucket': os.environ.get('STORAGE_BUCKET')
    })

_db_client = None

def get_db():
    global _db_client
    if _db_client is None:
        _db_client = firestore.client()
    return _db_client

def validate_request_data(data):
    if not isinstance(data, dict):
        return False, "genRequest must be a JSON object"

    input_video = data.get('inputVideo')
    if not isinstance(input_video, dict) or not input_video:
        return False, "inputVideo must be a non-empty dictionary map"
    
    valid_url_found = False
    for key, media in input_video.items():
        if not isinstance(media, dict) or 'url' not in media or not isinstance(media['url'], str):
            continue 
        if not media['url'].strip():
            continue
        valid_url_found = True
    
    if not valid_url_found:
        return False, "No valid video URLs found in inputVideo map"

    try:
        max_dur = int(data.get('maxDuration', 60))
        min_dur = int(data.get('minDuration', 15))
        num_clips = int(data.get('numberOfClips', 3))
    except (ValueError, TypeError):
        return False, "Duration and clip counts must be integers"

    if min_dur < 5:
        return False, "minDuration must be at least 5 seconds"
    if max_dur > 300:
        return False, "maxDuration cannot exceed 300 seconds"
    if min_dur >= max_dur:
        return False, "minDuration must be less than maxDuration"
    if not (1 <= num_clips <= 10):
        return False, "numberOfClips must be between 1 and 10"

    aspect_ratio = data.get('aspectRatio', '9:16')
    if aspect_ratio not in ['9:16', '16:9', '1:1', '4:5']:
        return False, f"Unsupported aspect ratio: {aspect_ratio}"

    return True, None


@functions_framework.http
def createShortsJob(request):
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    headers = {'Access-Control-Allow-Origin': '*'}

    user_id = None
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401, headers

        parts = auth_header.split()
        if len(parts) < 2 or parts[0].lower() != 'bearer':
            return jsonify({"error": "Invalid Header Format"}), 401, headers

        token_str = parts[1]
        decoded_token = auth.verify_id_token(token_str)
        user_id = decoded_token['uid']
            
    except Exception as e:
        return jsonify({"error": "Authentication Failed", "details": str(e)}), 401, headers

    try:
        db = get_db()
    except Exception as e:
        return jsonify({"error": "Database Connection Failed"}), 500, headers

    os.chdir('/tmp')

    try:
        from google import genai
        from scripts.whisper_gen import generate_whisperx
        from scripts import (
            download_video, 
            create_viral_segments, 
            cut_segments, 
            edit_video, 
            transcribe_cuts, 
            adjust_subtitles, 
            burn_subtitles
        )
        from scripts.credits_manager import check_credits_transaction, consume_credits_transaction, refund_credits_transaction

    except ImportError as e:
        return jsonify({"error": f"Server Configuration Error: Missing dependency {e}"}), 500, headers

    PROJECT_ID = os.environ.get("GCLOUD_PROJECT") 
    LOCATION = "us-central1"
    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    except Exception as e:
        print(f"Warning: GenAI Client init failed: {e}")
        client = None

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

    total_reserved_videos = 0
    successful_videos = 0
    
    try:
        request_json = request.get_json(silent=True)
        if not request_json or 'shortBuildId' not in request_json:
            return jsonify({"error": "Missing shortBuildId parameter"}), 400, headers
        
        short_build_id = request_json['shortBuildId']
        user_ref = db.collection('users').document(user_id)
        
        doc_ref = user_ref.collection('generatedShorts').document(short_build_id)
        doc_snapshot = doc_ref.get()

        if not doc_snapshot.exists:
            return jsonify({"error": "Build ID not found in database"}), 404, headers

        build_data = doc_snapshot.to_dict()
        gen_request = build_data.get('genRequest', {})

        is_valid, error_msg = validate_request_data(gen_request)
        if not is_valid:
            return jsonify({"error": "Validation Error", "details": error_msg}), 400, headers

        input_videos_map = gen_request.get('inputVideo', {})
        urls = [m['url'] for m in input_videos_map.values() if 'url' in m and m['url'].strip()]
        
        max_duration = int(gen_request.get('maxDuration', 60))
        min_duration = int(gen_request.get('minDuration', 15))
        num_clips = int(gen_request.get('numberOfClips', 3))
        aspect_ratio = gen_request.get('aspectRatio', '9:16')
        instructions = gen_request.get('customPrompt', None)
        watermark_text = gen_request.get('watermarkText', "")

        total_reserved_videos = num_clips * len(urls)
        
        try:
            transaction = db.transaction()
            check_credits_transaction(transaction, user_ref, video_credits=total_reserved_videos, image_credits=0, text_credits=0)
        except ValueError as ve:
             return jsonify({"error": "Insufficient Credits", "details": str(ve)}), 402, headers
        except Exception as e:
             return jsonify({"error": "Transaction Failed", "details": str(e)}), 500, headers

        for vid_url in urls:
            folders = ['all', 'archive', 'tmp', 'final', 'subs', 'subs_ass', 'burned_sub']
            for d in folders:
                if os.path.exists(d):
                    shutil.rmtree(d)
                os.makedirs(d, exist_ok=True)

            try:
                print(f"Downloading: {vid_url}")
                input_video_path = download_video.download(vid_url)
                if not input_video_path or not os.path.exists(input_video_path):
                     raise FileNotFoundError("Video download failed")
                shutil.copy2(input_video_path, "tmp/input_video.mp4")
                
                generate_whisperx("tmp/input_video.mp4", 'tmp')
                
                viral_data = create_viral_segments.create_viral_segments(
                    num_segments=num_clips, 
                    instructions=instructions, 
                    tempo_minimo=min_duration, 
                    tempo_maximo=max_duration, 
                    client=client,
                )
                
                if not viral_data or "segments" not in viral_data or not viral_data["segments"]:
                    print(f"No viral segments found for {vid_url}")
                    continue

                cut_segments.cut(viral_data["segments"])
                edit_video.editv2(aspectRatio=aspect_ratio)
                
                transcribe_cuts.transcribe()
                adjust_subtitles.adjust(
                    STYLE_CONFIG['base_color'], STYLE_CONFIG['base_size'], STYLE_CONFIG['h_size'], 
                    STYLE_CONFIG['highlight_color'], STYLE_CONFIG['palavras_por_bloco'], 
                    STYLE_CONFIG['limite_gap'], STYLE_CONFIG['modo'], STYLE_CONFIG['posicao_vertical'], 
                    STYLE_CONFIG['alinhamento'], STYLE_CONFIG['fonte'], STYLE_CONFIG['contorno'], 
                    STYLE_CONFIG['cor_da_sombra'], STYLE_CONFIG['negrito'], 
                    0, 0, 0, 1, 5, 1
                )
                
                burn_subtitles.burn_with_title_and_channel(
                    optional_header=None, 
                    segments=viral_data["segments"], 
                    font_size=100, 
                    channel_name=watermark_text
                )

                bucket = storage.bucket()
                generated_count_for_url = 0
                
                for i in range(len(viral_data["segments"])):
                    fpath = f"burned_sub/final-output{str(i).zfill(3)}_processed.mp4"
                    
                    if os.path.exists(fpath):
                        unique_id = str(uuid.uuid4())
                        file_name = f"short_{unique_id}.mp4"
                        blob_path = f"users/{user_id}/generatedShorts/{short_build_id}/{file_name}"
                        
                        blob = bucket.blob(blob_path)
                        blob.upload_from_filename(fpath)
                        
                        media_data = {
                            "url": blob_path, 
                            "mimeType": "video/mp4",
                            "type": "generated",
                            "generatedAt": firestore.SERVER_TIMESTAMP
                        }
                        
                        doc_ref.set({
                            "shorts": { unique_id: media_data },
                            "lastUpdatedAt": firestore.SERVER_TIMESTAMP
                        }, merge=True)
                        generated_count_for_url += 1
                
                successful_videos += generated_count_for_url

            except Exception as inner_e:
                print(f"Error processing video {vid_url}: {inner_e}")
                continue
                
            finally:
                for folder in folders:
                    if os.path.exists(folder):
                        shutil.rmtree(folder)

        try:
            if successful_videos > 0:
                transaction_consume = db.transaction()
                consume_credits_transaction(transaction_consume, user_ref, video_credits=successful_videos, image_credits=0, text_credits=0)
            
            refund_amount = total_reserved_videos - successful_videos
            if refund_amount > 0:
                transaction_refund = db.transaction()
                refund_credits_transaction(transaction_refund, user_ref, video_credits=refund_amount, image_credits=0, text_credits=0)

        except Exception as credit_error:
            return jsonify({"error": "Internal Server Error", "details": str(credit_error)}), 500, headers
        
        if successful_videos != total_reserved_videos:
            return jsonify({"error": "Internal Server Error", "details": "Mismatch in generated video count"}), 500, headers

        return jsonify({
            "message": "Job Completed",
            "buildId": short_build_id,
            "videosGenerated": successful_videos,
            "videosRequested": total_reserved_videos
        }), 200, headers

    except Exception as e:
        print(f"Global Job Failure: {e}")
        if user_id and total_reserved_videos > 0:
            try:
                db = get_db()
                user_ref = db.collection('users').document(user_id)
                if successful_videos == 0: 
                    transaction_refund = db.transaction()
                    refund_credits_transaction(transaction_refund, user_ref, video_credits=total_reserved_videos, image_credits=0, text_credits=0)
            except Exception as refund_error:
                print(f"CRITICAL: Failed to refund credits after error: {refund_error}")

        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500, headers