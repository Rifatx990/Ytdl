from fastapi import FastAPI, HTTPException, Query
from pytube import YouTube
from threading import Timer
import os
import uuid

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "FastAPI YouTube Downloader is running!"}

@app.get("/download")
async def download_video(
    url: str,
    format: str = Query("video", regex="^(video|audio)$")
):
    try:
        yt = YouTube(url)

        # Generate unique filename (without extension)
        unique_id = str(uuid.uuid4())

        if format == "audio":
            stream = yt.streams.filter(only_audio=True).first()
            file_path = stream.download(filename=f"{unique_id}.mp4")
            # Rename to .mp3 (optional, since it’s audio only)
            base, ext = os.path.splitext(file_path)
            new_file_path = f"{base}.mp3"
            os.rename(file_path, new_file_path)
            file_path = new_file_path
        else:
            stream = yt.streams.get_highest_resolution()
            file_path = stream.download(filename=f"{unique_id}.mp4")

        # Auto delete after 10 minutes
        Timer(600, lambda: os.remove(file_path) if os.path.exists(file_path) else None).start()

        return {
            "message": f"{format.capitalize()} downloaded successfully!",
            "filename": os.path.basename(file_path)
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error downloading: {str(e)}")
