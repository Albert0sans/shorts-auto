import json
import os
import time
import random
import re
from google import genai
from google.genai.errors import APIError

def ask_gemini_flash_2_5(client, prompt: str, retries=3) -> str:
    """
    Sends a prompt to the gemini-2.5-flash cloud model with retry logic.
    """
    print("ask_gemini_flash_2_5")
    if client is None:
        print("Error: Client is None")
        return ""

    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    {
                        'role': 'user',
                        'parts': [{'text': prompt}],
                    },
                ],
            )
            return response.text
        except APIError as e:
            print(f"Gemini API Error (Attempt {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt + random.uniform(0, 1))
            else:
                print(f"Failed after {retries} attempts.")
                return ""
        except Exception as e:
            print(f"Unexpected error: {e}")
            return ""
    return ""

def extract_json(text):
    """
    Robustly extracts JSON object from a string using regex, 
    handling potential markdown text or extra whitespace.
    """
    if not text:
        return None
    try:
        # Find the first opening brace and the last closing brace
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        # Fallback: try parsing the whole text
        return json.loads(text)
    except json.JSONDecodeError:
        print("Failed to decode JSON from response.")
        return None

def create_viral_segments(num_segments, instructions, tempo_minimo, tempo_maximo, client):
    """
    Analyzes a video transcript to generate prompts for an AI to identify potential viral segments.
    """
    output_txt_file = "tmp/viral_segments.txt"
    if os.path.exists(output_txt_file):
        return read_json_file(output_txt_file)
    
    try:
        with open('tmp/input_video.tsv', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print("Error: 'tmp/input_video.tsv' not found.")
        return {"segments": [], "tags": []}

    system_prompt = (
        "You are a Viral Segment Identifier professional that analyzes a video's transcript and predicts which segments "
        "might go viral on social media platforms. You use factors such as emotional impact, humor, unexpected content, "
        "and relevance to current trends to make your predictions. You return a structured JSON document detailing the "
        "start and end times, description, duration, and a viral score for the potential viral segments."
        f"Special Instructions MUST FOLLOW ALWAYS: {instructions}"
    )

    # Simplified template to avoid confusion
    json_template = '''
{
    "tags": [
        "tag1", "tag2", "tag3"
    ],
    "segments": [
        {
            "title": "Suggested Viral Title max 4 words",
            "start_time": 0,
            "end_time": 1000,
            "score": 95,
            "duration": 10
        }
    ]
}
'''
    chunk_size = 120000
    chunks = []
    start = 0
    if len(content) > chunk_size:
        while start < len(content):
            end = content.rfind('\n', start, start + chunk_size)
            if end == -1 or end <= start:
                end = start + chunk_size
            chunks.append(content[start:min(end, len(content))])
            start = end + 1
    else:
        chunks.append(content)

    analysis_type = f"identify at least {num_segments} distinct text segments that are either viral or potentially viral, focusing on the most engaging content"

    output_prompts = []
    total_chunks = len(chunks)

    for i, chunk in enumerate(chunks):
        chunk_context_info = ""
        if total_chunks > 1:
            chunk_context_info = f"\n\nNOTE: This is part {i + 1} of {total_chunks} of a larger transcript. Analyze this section independently."

        # REMOVED markdown code blocks around json_template
        prompt = f"""
{system_prompt}{chunk_context_info}

## INSTRUCTIONS
1.  Carefully read the provided video transcript below, which includes start and end times in milliseconds for each line.
2.  Your task is to {analysis_type}.
2a. You **MUST** ignore each episode intro song and do not include it in the segments.
2a. You **MUST** return a list of segments that totals at least **{num_segments}** segments.
3.  Each identified segment MUST have a minimum duration of {tempo_minimo} and maximum of {tempo_maximo} seconds.
4.  Segments MUST not overlap.
6.  The cuts **MUST** make logical sense and should not end abruptly.
7.  The 'title' in your response must be in the same language as the transcript.
8.  Your final output must be ONLY the JSON structure provided below. Do not add explanations.

## TRANSCRIPT CHUNK
{chunk}

## JSON OUTPUT FORMAT
Based on your analysis, provide your response in the following JSON format:
{json_template}
"""
        output_prompts.append(prompt)

    viral_segments = []
    tags = []

    for viral_segment_prompt in output_prompts:
        response_text = ask_gemini_flash_2_5(client, viral_segment_prompt)
        print(f"Gemini Response Length: {len(response_text)}")
        
        json_data = extract_json(response_text)
        
        if json_data:
            current_tags = json_data.get("tags", [])
            if current_tags:
                tags = current_tags # Update tags (or extend if you prefer)
            
            segments = json_data.get("segments", [])
            viral_segments.extend(segments)
        else:
             print("Skipping chunk due to JSON parsing failure.")

    result_data = {
        "segments": viral_segments,
        "tags": tags
    }
    
    save_viral_segments(result_data)
    return result_data

def save_viral_segments(segments_data=None):
    output_txt_file = "tmp/viral_segments.txt"
    try:
        with open(output_txt_file, 'w', encoding='utf-8') as file:
            json.dump(segments_data, file, ensure_ascii=False, indent=4)
        print(f"Viral segments saved to {output_txt_file}\n")
    except Exception as e:
        print(f"Error saving viral segments: {e}")

def read_json_file(output_txt_file):
    try:
        with open(output_txt_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
        print(f"Error reading {output_txt_file}: {e}")
        return {"segments": [], "tags": []}