import os
import time
import yt_dlp

def download(url):
    name=url.split("/")[-1]
    name=name.split('.')[0]
    output_path = f'videos/{name}.mp4'
    
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat':'mp4'
        }],
        'outtmpl': output_path,
        'postprocessor_args': [
            '-movflags', 'faststart'
        ],
       'merge_output_format':'mp4'
    }
    if(os.path.exists(output_path)):
        return output_path
    MAX_RETRIES = 3
    retry_count = 0

    while retry_count < MAX_RETRIES:
        try:
            print(f"Attempting download (Attempt {retry_count + 1} of {MAX_RETRIES})...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # If download succeeds, break out of the loop
            print("Download successful.")
            break
            
        except yt_dlp.utils.DownloadError as e:
            retry_count += 1
            print(f"Download Error: {e}")
            
            if retry_count < MAX_RETRIES:
                print(f"Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print("Maximum retries reached. Download failed.")
                # You might want to raise the exception here if you want the program to stop
                raise e 

    return output_path