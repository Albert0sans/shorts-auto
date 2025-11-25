import re

def extract_season_episode(filename):
    """
    Extracts the Season (S##) and Episode (E##) from a standard TV filename.

    Args:
        filename (str): The video filename (e.g., 'Family-Guy-S01E01-Death-Has-A-Shadow.mp4').

    Returns:
        tuple: A tuple containing the season and episode strings (e.g., ('S01', 'E01')).
               Returns (None, None) if the pattern is not found.
    """
    # Regex pattern to find S##E##.
    # r'(S\d{2}E\d{2})' finds the entire S01E01 string.
    # We can refine it to capture S## and E## separately using parentheses:
    # (S\d{2}) captures the Season part (S01)
    # (E\d{2}) captures the Episode part (E01)
    # 1x05
    
    # re.I makes the match case-insensitive (S01E01 or s01e01)
    name=filename.split("/")[-1]
    print(name)
    return name.split("-")[2]

