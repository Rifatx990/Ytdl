from fastapi import FastAPI, HTTPException, Query
from pytube import YouTube
from fastapi.responses import FileResponse
import os
import uuid
import threading

app = FastAPI()

DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
COOKIE_PATH = os.path.join(os.getcwd(), "cookies.txt")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def delete_file_later(file_path: str, delay: int = 600):
    def delete():
        try:
            os.remove(file_path)
            print(f"Deleted: {file_path}")
        except Exception as e:
            print(f"Error deleting file: {e}")
    threading.Timer(delay, delete).start()

@app.get("/download")
async def download_media(
    url: str = Query(..., description="YouTube video URL"),
    format: str = Query("video", description="Choose 'video' or 'audio'")
):
    try:
        # Initialize YouTube with cookies (if exists)
        if os.path.exists(COOKIE_PATH):
            yt = YouTube(url, use_oauth=False, allow_oauth_cache=True, cookies=COOKIE_PATH)
        else:
            yt = YouTube(url)

        unique_filename = str(uuid.uuid4())
        file_ext = "mp3" if format == "audio" else "mp4"
        filename = f"{unique_filename}.{file_ext}"
        file_path = os.path.join(DOWNLOAD_DIR, filename)

        stream = yt.streams.filter(only_audio=True).first() if format == "audio" else yt.streams.get_highest_resolution()
        stream.download(output_path=DOWNLOAD_DIR, filename=filename)

        delete_file_later(file_path)

        return FileResponse(file_path, media_type="application/octet-stream", filename=filename)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error downloading: {str(e)}")
