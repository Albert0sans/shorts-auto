import os
import json

def save_viral_segments(segments_data=None):
    output_txt_file = "tmp/viral_segments.txt"

    
    with open(output_txt_file, 'w', encoding='utf-8') as file:
                json.dump(segments_data, file, ensure_ascii=False, indent=4)
                print(f"Segmentos virais salvos em {output_txt_file}\n")
    