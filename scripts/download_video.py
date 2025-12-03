import os
from firebase_admin import storage

def download(storage_path):
    blob_path = storage_path.lstrip('/')
    filename = os.path.basename(blob_path)
    os.makedirs('videos', exist_ok=True)
    output_path = os.path.join('videos', filename)

    if os.path.exists(output_path):
        return output_path

    bucket = storage.bucket()
    blob = bucket.blob(blob_path)
    blob.download_to_filename(output_path)

    return output_path