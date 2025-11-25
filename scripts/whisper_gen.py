import csv
import os
import subprocess

from scripts.get_audio import get_audio

def generate_whisperx(input_file, output_folder, model='large-v3'):
        json_file = os.path.join(output_folder, f"{os.path.splitext(os.path.basename(input_file))[0]}.json")  # Define the JSON output file

        # Skip processing if the JSON file already exists
        if os.path.exists(json_file):
            return
        command = [
            "whisperx",
            input_file,
            "--model", model,
            "--task", "transcribe",
            "--align_model", "WAV2VEC2_ASR_LARGE_LV60K_960H",
            "--chunk_size", "10",
            "--vad_onset", "0.4",
            "--vad_offset", "0.3",
            "--compute_type", "float32",
            "--batch_size", "10",
            "--verbose", "False",
            "--output_dir", output_folder,
            "--output_format", "all",
            "--device", "cpu" 
        ]
        
        result = subprocess.run(command, check=True, text=True, capture_output=True)

        if result.returncode != 0:
            print(result.stderr)
        else:
            print(result.stdout)  


def csv_to_tsv(input_file):
    """
    Reads a CSV file and writes its content to a new TSV file.

    The new TSV file will have the same name as the input file,
    but with a '.tsv' extension.

    Args:
        input_file (str): The path to the input CSV file.

    Returns:
        str: The path to the newly created TSV file, or None if an error occurs.
    """
    # Create the output file name by changing the extension to .tsv
    base, _ = os.path.splitext(input_file)
    output_file = base + ".tsv"

    try:
        # Open the CSV file for reading
        with open(input_file, mode='r', newline='', encoding='utf-8') as csvfile:
            # Use the csv.reader to correctly handle commas inside quotes
            reader = csv.reader(csvfile)

            # Open the TSV file for writing
            with open(output_file, mode='w', newline='', encoding='utf-8') as tsvfile:
                # Use the csv.writer, specifying 'tab' as the delimiter
                writer = csv.writer(tsvfile, delimiter='\t')

                # Iterate over the rows and write them to the TSV file
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
    
    
    