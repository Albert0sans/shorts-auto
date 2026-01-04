import os
import shutil
import uuid
import tempfile
import contextlib
import math
import subprocess
import functions_framework
from flask import jsonify
import firebase_admin
from firebase_admin import storage, auth, firestore

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

DEFAULT_STYLE_CONFIG = {
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
    'negrito': 1,
    'italico': 0,
    'sublinhado': 0,
    'tachado': 0,
    'estilo_da_borda': 1,
    'espessura_do_contorno': 1,
    'tamanho_da_sombra': 0,
    'uppercase': False
}

def hex_to_ass_color(hex_color):
    if not hex_color or not isinstance(hex_color, str):
        return None
    
    clean_hex = hex_color.lstrip('#')
    if len(clean_hex) != 6:
        return None
    
    r = clean_hex[0:2]
    g = clean_hex[2:4]
    b = clean_hex[4:6]
    
    return f"&H{b}{g}{r}&"

def get_merged_style_config(user_settings):
    config = DEFAULT_STYLE_CONFIG.copy()
    
    if not user_settings or not isinstance(user_settings, dict):
        return config

    if 'textColor' in user_settings:
        ass_color = hex_to_ass_color(user_settings['textColor'])
        if ass_color:
            config['base_color'] = ass_color

    if 'highlightColor' in user_settings:
        ass_color = hex_to_ass_color(user_settings['highlightColor'])
        if ass_color:
            config['highlight_color'] = ass_color

    if 'outlineColor' in user_settings:
        ass_color = hex_to_ass_color(user_settings['outlineColor'])
        if ass_color:
            config['contorno'] = ass_color

    if 'shadowColor' in user_settings:
        ass_color = hex_to_ass_color(user_settings['shadowColor'])
        if ass_color:
            config['cor_da_sombra'] = ass_color

    if 'fontSize' in user_settings:
        try:
            size = int(user_settings['fontSize'])
            config['base_size'] = size
            config['h_size'] = size + 2
        except (ValueError, TypeError):
            pass

    if 'fontFamily' in user_settings:
        config['fonte'] = user_settings['fontFamily']

    if 'yPosition' in user_settings:
        try:
            config['posicao_vertical'] = int(user_settings['yPosition'])
        except (ValueError, TypeError):
            pass

    if 'wordsPerLine' in user_settings:
        try:
            config['palavras_por_bloco'] = int(user_settings['wordsPerLine'])
        except (ValueError, TypeError):
            pass

    if 'gapLimit' in user_settings:
        try:
            config['limite_gap'] = float(user_settings['gapLimit'])
        except (ValueError, TypeError):
            pass

    if 'alignment' in user_settings:
        try:
            config['alinhamento'] = int(user_settings['alignment'])
        except (ValueError, TypeError):
            pass

    if 'mode' in user_settings:
        config['modo'] = user_settings['mode']

    if 'isBold' in user_settings:
        config['negrito'] = 1 if user_settings['isBold'] else 0

    if 'isItalic' in user_settings:
        config['italico'] = 1 if user_settings['isItalic'] else 0

    if 'isUnderScore' in user_settings:
        config['sublinhado'] = 1 if user_settings['isUnderScore'] else 0

    if 'isStrikeOut' in user_settings:
        config['tachado'] = 1 if user_settings['isStrikeOut'] else 0

    if 'borderStyle' in user_settings:
        try:
            config['estilo_da_borda'] = int(user_settings['borderStyle'])
        except (ValueError, TypeError):
            pass

    if 'outlineWidth' in user_settings:
        try:
            config['espessura_do_contorno'] = float(user_settings['outlineWidth'])
        except (ValueError, TypeError):
            pass

    if 'shadowSize' in user_settings:
        try:
            config['tamanho_da_sombra'] = float(user_settings['shadowSize'])
        except (ValueError, TypeError):
            pass
            
    if 'uppercase' in user_settings:
        config['uppercase'] = bool(user_settings['uppercase'])

    if 'highlightCurrentWord' in user_settings:
        if user_settings['highlightCurrentWord'] is False:
             config['modo'] = "simple"

    return config

@contextlib.contextmanager
def temporary_work_dir():
    prev_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        try:
            yield temp_dir
        finally:
            os.chdir(prev_cwd)

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

    aspect_ratio = data.get('aspectRatio')
    if aspect_ratio and aspect_ratio not in ['9:16', '16:9', '1:1', '4:5']:
        return False, f"Unsupported aspect ratio: {aspect_ratio}"

    return True, None

def createShortsJob(request):
    savingCollection = "generatedShorts"
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

    try:
        from google import genai
        from scripts.credits_manager import get_credit_costs
        from scripts.change_run_status import ChangeDDBBStatus
        from scripts.whisper_gen import generate_whisperx
        from scripts import (
            download_video, 
            create_viral_segments, 
            cut_segments, 
            transcribe_cuts, 
            adjust_subtitles, 
            burn_subtitles
        )
        from scripts.credits_manager import check_credits_transaction, consume_credits_transaction, refund_credits_transaction

    except ImportError as e:
        return jsonify({"error": f"Server Configuration Error: Missing dependency {e}"}), 500, headers

    project_id = os.environ.get("GCLOUD_PROJECT") 
    location = "us-central1"
    
    try:
        client = genai.Client(vertexai=True, project=project_id, location=location)
    except Exception as e:
        print(f"Warning: GenAI Client init failed: {e}")
        client = None

    total_reserved_videos = 0
    successful_videos = 0
    short_build_id = None
    
    shorts_unit_cost = 5 
    
    try:
        request_json = request.get_json(silent=True)
        if not request_json or 'shortBuildId' not in request_json:
            return jsonify({"error": "Missing shortBuildId parameter"}), 400, headers
        
        short_build_id = request_json['shortBuildId']
        
        ChangeDDBBStatus(db, user_id=user_id, short_build_id=short_build_id, new_status="running", collection=savingCollection)


        user_ref = db.collection('users').document(user_id)
        doc_ref = user_ref.collection(savingCollection).document(short_build_id)
        doc_snapshot = doc_ref.get()

        if not doc_snapshot.exists:
            return jsonify({"error": "Build ID not found in database"}), 404, headers

        build_data = doc_snapshot.to_dict()
        gen_request = build_data.get('genRequest', {})
        subtitles_styles = gen_request.get('subtitlesStyles', gen_request.get('subtitleSettings', {}))

        is_valid, error_msg = validate_request_data(gen_request)
        if not is_valid:
            ChangeDDBBStatus(db, user_id=user_id, short_build_id=short_build_id, new_status="failed", status_msg=error_msg, collection=savingCollection)
            return jsonify({"error": "Validation Error", "details": error_msg}), 400, headers

        input_videos_map = gen_request.get('inputVideo', {})
        urls = [m['url'] for m in input_videos_map.values() if 'url' in m and m['url'].strip()]
        
        max_duration = int(gen_request.get('maxDuration', 60))
        min_duration = int(gen_request.get('minDuration', 15))
        num_clips = int(gen_request.get('numberOfClips', 3))
        aspect_ratio = gen_request.get('aspectRatio')
        instructions = gen_request.get('customPrompt', None)
        watermark_text = gen_request.get('watermarkText', "")
        optional_header = gen_request.get('optional_header', "")

        costs = get_credit_costs(db)
        shorts_unit_cost = costs.get("shorts_generation_cost", 5)

        total_reserved_videos = num_clips * len(urls)
        total_credit_cost = total_reserved_videos * shorts_unit_cost
        
        try:
            transaction = db.transaction()
            check_credits_transaction(transaction, user_ref, credits=total_credit_cost)
        except ValueError as ve:
             ChangeDDBBStatus(db, user_id=user_id, short_build_id=short_build_id, new_status="failed", status_msg=str(ve), collection=savingCollection)
             
             return jsonify({"error": "Insufficient Credits", "details": str(ve)}), 402, headers
        except Exception as e:
             ChangeDDBBStatus(db, user_id=user_id, short_build_id=short_build_id, new_status="failed", status_msg=str(e), collection=savingCollection)
             return jsonify({"error": "Transaction Failed", "details": str(e)}), 500, headers

        current_style_config = get_merged_style_config(subtitles_styles)

        with temporary_work_dir() as temp_dir:
            
            required_folders = ['tmp', 'subs', 'subs_ass', 'burned_sub', 'videos']
                
            bucket = storage.bucket()
            
            for vid_url in urls:
                for folder in required_folders:
                    if os.path.exists(folder):
                        shutil.rmtree(folder)
                    os.makedirs(folder, exist_ok=True)

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
                    
                    transcribe_cuts.transcribe(input_folder='tmp', output_folder='subs')
                    
                    adjust_subtitles.adjust(
                        current_style_config['base_color'], 
                        current_style_config['base_size'], 
                        current_style_config['h_size'], 
                        current_style_config['highlight_color'], 
                        current_style_config['palavras_por_bloco'], 
                        current_style_config['limite_gap'], 
                        current_style_config['modo'], 
                        current_style_config['posicao_vertical'], 
                        current_style_config['alinhamento'], 
                        current_style_config['fonte'], 
                        current_style_config['contorno'], 
                        current_style_config['cor_da_sombra'], 
                        current_style_config['negrito'],
                        current_style_config['italico'],
                        current_style_config['sublinhado'],
                        current_style_config['tachado'],
                        current_style_config['estilo_da_borda'],
                        current_style_config['espessura_do_contorno'],
                        current_style_config['tamanho_da_sombra']
                    )
                    
                    burn_subtitles.burn_with_title_and_channel(
                        optional_header=optional_header, 
                        segments=viral_data["segments"], 
                        font_size=100, 
                        channel_name=watermark_text,
                        aspect_ratio=aspect_ratio
                    )

                    generated_count_for_url = 0
                    for i in range(len(viral_data["segments"])):
                        fpath = f"burned_sub/final-output{str(i).zfill(3)}_processed.mp4"
                        
                        if os.path.exists(fpath):
                            unique_id = str(uuid.uuid4())
                            file_name = f"short_{unique_id}.mp4"
                            blob_path = f"users/{user_id}/{savingCollection}/{short_build_id}/{file_name}"
                            
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
                
        try:
            if successful_videos > 0:
                credits_to_consume = successful_videos * shorts_unit_cost
                transaction_consume = db.transaction()
                consume_credits_transaction(transaction_consume, user_ref, credits=credits_to_consume)
            
            failed_count = total_reserved_videos - successful_videos
            if failed_count > 0:
                credits_to_refund = failed_count * shorts_unit_cost
                transaction_refund = db.transaction()
                refund_credits_transaction(transaction_refund, user_ref, credits=credits_to_refund)
            
            final_status = "completed" if successful_videos == total_reserved_videos else "failed"
            if successful_videos > 0 and successful_videos < total_reserved_videos:
                 final_status = "completed" 
            failed_message = f"{total_reserved_videos - successful_videos} Failed videos"
            ChangeDDBBStatus(db, user_id=user_id, short_build_id=short_build_id, new_status=final_status, status_msg=failed_message, collection=savingCollection)

        except Exception as credit_error:
            return jsonify({"error": "Internal Server Error during Credit Adjustment", "details": str(credit_error)}), 500, headers
        
        response_data = {
            "message": "Job Processed",
            "buildId": short_build_id,
            "videosGenerated": successful_videos,
            "videosRequested": total_reserved_videos
        }
        
        if successful_videos != total_reserved_videos:
            response_data["warning"] = "Partial success or failure in some segments."
            
        
        return jsonify(response_data), 200, headers

    except Exception as e:
        print(f"Global Job Failure: {e}")
        if user_id and total_reserved_videos > 0 and successful_videos == 0:
            try:
                db = get_db()
                user_ref = db.collection('users').document(user_id)
                credits_to_refund = total_reserved_videos * shorts_unit_cost
                transaction_refund = db.transaction()
                refund_credits_transaction(transaction_refund, user_ref, credits=credits_to_refund)
                if short_build_id:
                    ChangeDDBBStatus(db, user_id=user_id, short_build_id=short_build_id, new_status="failed", status_msg=str(e), collection=savingCollection)
            except Exception as refund_error:
                print(f"CRITICAL: Failed to refund credits after error: {refund_error}")

        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500, headers

def createSubtitlesJob(request):
    savingCollection = "generatedSubtitles"
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

    try:
        from scripts.change_run_status import ChangeDDBBStatus
        from scripts.whisper_gen import generate_whisperx
        from scripts import (
            download_video,
            burn_subtitles,
            transcribe_cuts,
            adjust_subtitles
        )
        from scripts.credits_manager import get_credit_costs
        from scripts.credits_manager import check_credits_transaction, consume_credits_transaction
    except ImportError as e:
        return jsonify({"error": f"Server Configuration Error: Missing dependency {e}"}), 500, headers

    subtitles_build_id = None
    
    try:
        request_json = request.get_json(silent=True)
        if not request_json or 'subtitlesBuildId' not in request_json:
            return jsonify({"error": "Missing subtitlesBuildId parameter"}), 400, headers
        
        subtitles_build_id = request_json['subtitlesBuildId']
        
        ChangeDDBBStatus(db, user_id=user_id, short_build_id=subtitles_build_id, new_status="running", collection=savingCollection)

        user_ref = db.collection('users').document(user_id)
        doc_ref = user_ref.collection(savingCollection).document(subtitles_build_id)
        doc_snapshot = doc_ref.get()

        if not doc_snapshot.exists:
            return jsonify({"error": "Build ID not found in database"}), 404, headers

        build_data = doc_snapshot.to_dict()
        gen_request = build_data.get('genRequest', {})
        subtitles_styles = gen_request.get('subtitlesStyles', gen_request.get('subtitleSettings', {}))
        
        input_videos_map = gen_request.get('inputVideo', {})
        urls = [m['url'] for m in input_videos_map.values() if 'url' in m and m['url'].strip()]
        
        watermark_text = gen_request.get('watermarkText', "")
        aspect_ratio = gen_request.get('aspectRatio')

        if not urls:
             ChangeDDBBStatus(db, user_id=user_id, short_build_id=subtitles_build_id, new_status="failed", status_msg="No valid input video URLs found", collection=savingCollection)
             return jsonify({"error": "No valid input video URLs found"}), 400, headers

        costs = get_credit_costs(db)
        subtitles_unit_cost = costs.get("subtitles_generation_cost", 1)

        total_credits_consumed = 0
        successful_videos = 0
        
        current_style_config = get_merged_style_config(subtitles_styles)

        with temporary_work_dir() as temp_dir:
            required_folders = ['tmp', 'subs', 'subs_ass', 'burned_sub'] 
            bucket = storage.bucket()
            
            for vid_url in urls:
                for folder in required_folders:
                    if os.path.exists(folder):
                        shutil.rmtree(folder)
                    os.makedirs(folder, exist_ok=True)

                try:
                    print(f"Downloading for subtitles: {vid_url}")
                    input_video_path = download_video.download(vid_url)
                    if not input_video_path or not os.path.exists(input_video_path):
                        print(f"Video download failed for {vid_url}")
                        continue
                    
                    shutil.copy2(input_video_path, "tmp/output000_original_scale.mp4")

                    cmd = [
                        'ffprobe', 
                        '-v', 'error', 
                        '-show_entries', 'format=duration', 
                        '-of', 'default=noprint_wrappers=1:nokey=1', 
                        "tmp/output000_original_scale.mp4"
                    ]
                    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    try:
                        duration_seconds = float(process.stdout)
                    except (ValueError, TypeError):
                        print(f"Could not determine duration for {vid_url}")
                        continue

                    duration_minutes = math.ceil(duration_seconds / 60)
                    current_video_cost = duration_minutes * subtitles_unit_cost

                    try:
                        transaction = db.transaction()
                        check_credits_transaction(transaction, user_ref, credits=current_video_cost)
                    except ValueError as ve:
                        print(f"Insufficient credits for video {vid_url}: {ve}")
                        continue

                    generate_whisperx("tmp/output000_original_scale.mp4", 'tmp')

                    transcribe_cuts.transcribe(input_folder='tmp', output_folder='subs')
                    
                    adjust_subtitles.adjust(
                        current_style_config['base_color'], 
                        current_style_config['base_size'], 
                        current_style_config['h_size'], 
                        current_style_config['highlight_color'], 
                        current_style_config['palavras_por_bloco'], 
                        current_style_config['limite_gap'], 
                        current_style_config['modo'], 
                        current_style_config['posicao_vertical'], 
                        current_style_config['alinhamento'], 
                        current_style_config['fonte'], 
                        current_style_config['contorno'], 
                        current_style_config['cor_da_sombra'], 
                        current_style_config['negrito'], 
                        current_style_config['italico'],
                        current_style_config['sublinhado'],
                        current_style_config['tachado'],
                        current_style_config['estilo_da_borda'],
                        current_style_config['espessura_do_contorno'],
                        current_style_config['tamanho_da_sombra']
                    )
                    
                    segments=[{"title": ""}]
                    
                    burn_subtitles.burn_with_title_and_channel(
                        optional_header="", 
                        segments=segments, 
                        font_size=100, 
                        channel_name=watermark_text,
                        aspect_ratio=aspect_ratio,
                    )

                    generated_count_for_url = 0
                    fpath = f"burned_sub/final-output{str(0).zfill(3)}_processed.mp4"
                        
                    if os.path.exists(fpath):
                            unique_id = str(uuid.uuid4())
                            file_name = f"short_{unique_id}.mp4"
                            blob_path = f"users/{user_id}/{savingCollection}/{subtitles_build_id}/{file_name}"
                            
                            blob = bucket.blob(blob_path)
                            blob.upload_from_filename(fpath)
                            
                            media_data = {
                                "url": blob_path, 
                                "mimeType": "video/mp4",
                                "type": "generated",
                                "generatedAt": firestore.SERVER_TIMESTAMP
                            }
                            
                            doc_ref.set({
                                "results": { unique_id: media_data },
                                "lastUpdatedAt": firestore.SERVER_TIMESTAMP
                            }, merge=True)
                            generated_count_for_url += 1
                    
                    successful_videos += generated_count_for_url
                    
                    transaction_consume = db.transaction()
                    consume_credits_transaction(transaction_consume, user_ref, credits=current_video_cost)
                    
                    total_credits_consumed += current_video_cost

                except Exception as inner_e:
                    print(f"Error processing video {vid_url}: {inner_e}")
                    continue

        status = "completed" if successful_videos == len(urls) else "completed" if successful_videos > 0 else "failed"
        status_msg = None
        if successful_videos < len(urls):
            status_msg = f"Processed {successful_videos}/{len(urls)} videos"

        ChangeDDBBStatus(db, user_id=user_id, short_build_id=subtitles_build_id, new_status=status, status_msg=status_msg, collection=savingCollection)

        return jsonify({
            "message": "Subtitles Job Finished",
            "buildId": subtitles_build_id,
            "processed": successful_videos,
            "total": len(urls),
            "creditsConsumed": total_credits_consumed
        }), 200, headers

    except Exception as e:
        print(f"Global Subtitle Job Failure: {e}")
        if user_id and subtitles_build_id:
             try:
                 ChangeDDBBStatus(db, user_id=user_id, short_build_id=subtitles_build_id, new_status="failed", status_msg=str(e), collection=savingCollection)
             except Exception:
                 pass
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500, headers
    
@functions_framework.http
def router(request):
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    path = request.path.strip('/')
    
    if path == 'createShortsJob':
        return createShortsJob(request)
    elif path == 'createSubtitlesJob':
        return createSubtitlesJob(request)
    else:
        return jsonify({"error": f"Function not found: {path}"}), 404, {'Access-Control-Allow-Origin': '*'}