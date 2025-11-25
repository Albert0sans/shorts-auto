from hashlib import sha1

import os
import shutil
import time
from scripts.whisper_gen import generate_whisperx
from scripts import download_video, upload_yt, create_viral_segments, cut_segments, edit_video, transcribe_cuts, adjust_subtitles, burn_subtitles, extract_ep
from google import genai
from datetime import datetime, timedelta, timezone

def next_time(delta):
    now_utc = datetime.now(timezone.utc)

    next_hour = now_utc + timedelta(hours=delta)

    # Luego, ponemos los minutos, segundos y microsegundos a cero para que sea en punto.
    publish_at_dt = next_hour.replace(minute=0, second=0, microsecond=0)


    publish_time_iso = publish_at_dt.isoformat().replace('+00:00 Z')

    return publish_time_iso
channel_name="@dailytoonmix"



#API_KEY="AIzaSyD6y3eW8wZUlV849GuSzmStp8skVE1UlRQ"

#client=genai.Client(api_key=API_KEY)
PROJECT_ID = "gen-lang-client-0695494343"
LOCATION = "us-central1" 

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION
)

# Create necessary directories

os.makedirs('all', exist_ok=True)
os.makedirs('archive', exist_ok=True)


estilo_da_borda = 3  
espessura_do_contorno = 1.5  
tamanho_da_sombra = 10  
base_color='&HFFFFFF&'       
highlight_color='&H00FFFF&'   
base_size=12                
h_size=14                   
contorno='&H000000&'         
cor_da_sombra='&H000000&'   
estilo_da_borda=1            
espessura_do_contorno=5    
tamanho_da_sombra=1         


modo="highlight"            
fonte="Arial"   
alinhamento=2           
posicao_vertical=60        
palavras_por_bloco=3      
limite_gap=0.2          
negrito=1                  
italico=0                  
sublinhado=0                
tachado=0                     
upload_mode=True


    


def create_shorts(urls,title:str,channel_name=""):
    
    if(urls is not list):
        urls=[urls]
    for url in urls:
   
        os.makedirs('tmp', exist_ok=True)
        os.makedirs('final', exist_ok=True)
        os.makedirs('subs', exist_ok=True)
        os.makedirs('subs_ass', exist_ok=True)
        os.makedirs('burned_sub', exist_ok=True)
        saving_folder=title
        if(title == None):
            saving_folder=sha1(url.encode('utf-8')).hexdigest()

            try:
                
                title= extract_ep.extract_season_episode(url)
                
            except:
                
                title=None
    

        os.makedirs(f'all/{saving_folder}', exist_ok=True)
        num_segments = 40
                
        viral_mode = "yes"
            
        tempo_minimo = 20 
        tempo_maximo = 58 

        import datetime

        def print_timestamp(command_name):
            """Prints a timestamp and the name of the command that just finished."""
            # Get the current time and format it
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Print the statement
            print(f"[{current_time}] Command finished: {command_name}")

        # --- Command Sequence with Timestamps ---

        input_video = download_video.download(url)
        shutil.copy2(input_video,"tmp/input_video.mp4")
        input_video="tmp/input_video.mp4"
        print_timestamp("download_video.download")
        generate_whisperx(input_video,'tmp')
        print_timestamp("generate_whisperx")

        viral_segments = create_viral_segments.create_viral_segments(num_segments, viral_mode, None, tempo_minimo, tempo_maximo, client=client)
        viral_segments=viral_segments["segments"]
        print_timestamp("create_viral_segments.create_viral_segments")

        cut_segments.cut(viral_segments)
        print_timestamp("cut_segments.cut")

        edit_video.editv2()
        print_timestamp("edit_video.edit")
        
        transcribe_cuts.transcribe()
        print_timestamp("transcribe_cuts.transcribe")

        adjust_subtitles.adjust(base_color, base_size, h_size, highlight_color, palavras_por_bloco, limite_gap, modo, posicao_vertical, alinhamento, fonte, contorno, cor_da_sombra, negrito, italico, sublinhado, tachado, estilo_da_borda, espessura_do_contorno, tamanho_da_sombra)
        print_timestamp("adjust_subtitles.adjust")

        
        burn_subtitles.burn_with_title_and_channel(optional_header=title,segments=viral_segments,font_size=100,channel_name=channel_name )
        print_timestamp("burn_subtitles.burn")

        for i,segment in enumerate(viral_segments):
            file=f"burned_sub/final-output{str(i).zfill(3)}_processed.mp4"
            
            destination_file_path = os.path.join(f"all/{title}/", file.split('/')[-1])
            shutil.move(file, destination_file_path)
        shutil.copy2("tmp/viral_segments.txt", f"all/{title}/")
        break
        shutil.rmtree("tmp")
        shutil.rmtree("final")
        shutil.rmtree("subs_ass")
        shutil.rmtree("subs")
        shutil.rmtree("burned_sub")

if __name__ == "__main__":
    create_shorts("https://www.youtube.com/watch?v=eora7cQo67k","no dormiria tranquilo")