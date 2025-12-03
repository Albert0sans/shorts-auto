import json
import os
import os
from google import genai
from google.genai.errors import APIError # Import for better error handling


def ask_gemini_flash_2_5(client,prompt: str) -> str:
    """
    Sends a prompt to the gemini-2.5-flash cloud model using the Google GenAI SDK 
    and returns the response.

    Args:
        prompt: The question or instruction for the model.

    Returns:
        A string containing the model's generated answer.
        Returns an error message if the connection or API call fails.
    """
    print("ask_gemini_flash_2_5")
    if client is None:
        return "Gemini client is not initialized. Please check your API key."

    try:
        # The client.models.generate_content function sends a request to the cloud model
        response = client.models.generate_content(
            model='gemini-2.5-flash',  # Specifies the target cloud model
            contents=[
                {
                    'role': 'user',
                    'parts': [{'text': prompt}],
                },
            ],
            # Optional: You can add generation_config here if needed (e.g., temperature)
            # config={"temperature": 0.7} 
        )
  
        # Extract and return the content from the response
        return response.text
        
    except APIError as e:
        # Handle specific API errors (e.g., invalid key, rate limit)
        return f"Gemini API Error occurred: {e}"
    except Exception as e:
        # Handle other general errors
        return f"An unexpected error occurred: {e}"

    
def create_viral_segments(num_segments, instructions, tempo_minimo, tempo_maximo,client):
    """
    Analyzes a video transcript to generate prompts for an AI to identify potential viral segments.

    Args:
        num_segments (int): The desired number of viral segments to identify per chunk.
        viral_mode (bool): If True, searches for general virality. If False, searches based on themes.
        themes (str): A comma-separated string of themes to search for if viral_mode is False.
        tempo_minimo (int): The minimum duration in seconds for a segment.
        tempo_maximo (int): The maximum duration in seconds for a segment.

    Returns:
        list: A list of formatted prompt strings, one for each chunk of the transcript.
    """
    output_txt_file="tmp/viral_segments.txt"
    if(os.path.exists("tmp/viral_segments.txt")):
        return read_json_file(output_txt_file)
    try:
        with open('tmp/input_video.tsv', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print("Error: 'tmp/input_video.csv' not found. Please ensure the file exists.")
        return []

    # --- AI and Formatting Definitions ---
    system_prompt = (
        "You are a Viral Segment Identifier profesional that analyzes a video's transcript and predicts which segments "
        "might go viral on social media platforms. You use factors such as emotional impact, humor, unexpected content, "
        "and relevance to current trends to make your predictions. You return a structured JSON document detailing the "
        "start and end times, description, duration, and a viral score for the potential viral segments."
        f"Special Instructions MUST FOLLOW ALWAYS: {instructions}"
    )

    json_template = '''
{
    "tags":[
        list of 15 related tags for this video in a single line
    ],
    "segments": [
        {
            "title": 'Suggested Viral Title, short and engaging maximun 4 words, censor bad words',"start_time":start milliseconds , "end_time": end milliseconds , "score": virality score 0-100, "duration": seconds duration
        }
    ]
}
'''
    # --- Transcript Chunking Logic ---
    chunk_size = 120000
    chunks = []
    start = 0
    if len(content) > chunk_size:
        while start < len(content):
            # Find the last newline character before the chunk size limit
            end = content.rfind('\n', start, start + chunk_size)
            # If no newline is found or we're at the end, take the rest of the content
            if end == -1 or end <= start:
                end = start + chunk_size
            chunks.append(content[start:min(end, len(content))])
            start = end + 1
    else:
        chunks.append(content)

    analysis_type = f"identify at least {num_segments} distinct text segments that are either viral or potentially viral, focusing on the most engaging content"


    output_prompts = []
    total_chunks = len(chunks)

    # Create a complete prompt for each chunk
    for i, chunk in enumerate(chunks):
        # Add context for the AI if the transcript is split into multiple parts
        chunk_context_info = ""
        if total_chunks > 1:
            chunk_context_info = f"\n\nNOTE: This is part {i + 1} of {total_chunks} of a larger transcript. Analyze this section independently."

        prompt = f"""
{system_prompt}{chunk_context_info}

## INSTRUCTIONS
1.  Carefully read the provided video transcript below, which includes start and end times in milliseconds for each line.
2.  Your task is to {analysis_type}.
2a. You **MUST** ignore each episode intro song and do not include it in the segments
2a. You **MUST** return a list of segments that totals at least **{num_segments}** segments. If you cannot find {num_segments} truly viral segments, you may include high-potential or engaging-but-not-viral segments to meet the segment count.
3.  Each identified segment MUST have a minimun duration of {tempo_minimo} and maximun of {tempo_maximo} seconds.
4.  segments MUST not overlap.
6.  The cuts **MUST** make logical sense and should not end abruptly.
7.  The 'title' in your response must be in the same language as the transcript.
8.  Your final output must be ONLY the JSON structure provided in the format example, do not use chars that could break the json such as quotation marks. Do not add any extra text or explanations.
## TRANSCRIPT CHUNK
{chunk}
## JSON OUTPUT FORMAT
Based on your analysis, provide your response in the following JSON format:
```json
{json_template}
```
"""
        output_prompts.append(prompt)
    viral_segments=[]
    tags=[]
    for viral_segment_prompt in output_prompts:
        dart=ask_gemini_flash_2_5(client,viral_segment_prompt)
        print(dart)
        json_string = dart.strip().replace('json\n', '').replace('\n', '').replace('```', '')
        
        correct_json = json.loads(json_string)
        tags=correct_json["tags"]
        viral_segments.extend(correct_json["segments"])

    viral_segments={
        "segments":  viral_segments,
        "tags":tags
        
        }
    save_viral_segments(viral_segments)
    return viral_segments
    


def save_viral_segments(segments_data=None):
    output_txt_file = "tmp/viral_segments.txt"

    
    with open(output_txt_file, 'w', encoding='utf-8') as file:
                json.dump(segments_data, file, ensure_ascii=False, indent=4)
                print(f"Segmentos virais salvos em {output_txt_file}\n")
def read_json_file(output_txt_file):
    """
    Reads a file containing JSON data, parses it, and returns a 
    Python dictionary or list.
    """
    try:
        with open(output_txt_file, 'r', encoding='utf-8') as file:
            # json.load() reads the file and parses the JSON data
            data = json.load(file)
        return data # Returns a Python dictionary or list
    except FileNotFoundError:
        return f"Error: The file '{output_txt_file}' was not found."
    except json.JSONDecodeError:
        return f"Error: The file '{output_txt_file}' does not contain valid JSON."
    except Exception as e:
        return f"An error occurred while reading the file: {e}"
