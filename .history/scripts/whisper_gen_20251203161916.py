import torch
import whisperx
import os
import csv
import json
import gc 
import torch

torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

def generate_whisperx(input_file, output_folder, model_name='large-v3-turbo', compute_type='int8'):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    base_name = os.path.splitext(os.path.basename(input_file))[0]
    json_output_path = os.path.join(output_folder, f"{base_name}.json")
    
    if os.path.exists(json_output_path):
        print(f"Skipping: {json_output_path} already exists.")
        return

    os.makedirs(output_folder, exist_ok=True)
    print(f"Loading model {model_name} on {device}...")

    vad_options = {
        "vad_onset": 0.4,
        "vad_offset": 0.3
    }
    model = whisperx.load_model(
        model_name, 
        device=device,
        compute_type=compute_type,
        vad_options=vad_options
    )

    print(f"Transcribing {input_file}...")
    audio = whisperx.load_audio(input_file)
    
    result = model.transcribe(audio, batch_size=4)
    
    del model
    gc.collect() 

    print("Aligning...")
    model_a, metadata = whisperx.load_align_model(
        language_code=result["language"], 
        device=device
    )

    result = whisperx.align(
        result["segments"], 
        model_a, 
        metadata, 
        audio, 
        device=device, 
        return_char_alignments=False
    )

    del model_a
    gc.collect()

    print(f"Saving to {json_output_path}...")
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        
    tsv_output_path = os.path.join(output_folder, f"{base_name}.tsv")
    save_as_tsv(result["segments"], tsv_output_path)

    print("Done!")

def save_as_tsv(segments, path):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(["start", "end", "text"]) 
        for seg in segments:
            text = seg.get('text', '')
            if text:
                text = text.strip()
            writer.writerow([seg.get('start'), seg.get('end'), text])

def csv_to_tsv(input_file):
    base, _ = os.path.splitext(input_file)
    output_file = base + ".tsv"

    try:
        with open(input_file, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            with open(output_file, mode='w', newline='', encoding='utf-8') as tsvfile:
                writer = csv.writer(tsvfile, delimiter='\t')
                for row in reader:
                    writer.writerow(row)

        print(f"Successfully converted '{input_file}' to '{output_file}'")
        return output_file

    except FileNotFoundError:
        print(f"Error: The input file '{input_file}' was not found.")
        return None
    except Exception as e:
        print(f"An error occurred during conversion: {e}")
        return None