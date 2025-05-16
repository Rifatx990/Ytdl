from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pytube import YouTube
from threading import Timer
from collections import defaultdict
import os
import uuid
import time

app = FastAPI()

# Per-IP rate limiting
request_times = defaultdict(lambda: 0)
MIN_INTERVAL = 3  # seconds

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client_ip = request.client.host
    current_time = time.time()

    if current_time - request_times[client_ip] < MIN_INTERVAL:
        return JSONResponse(status_code=429, content={"detail": "Too many requests. Try again in a few seconds."})
    
    request_times[client_ip] = current_time
    response = await call_next(request)
    return response

@app.get("/")
@app.head("/")
async def root():
    return {"message": "FastAPI YouTube Downloader is running!"}

@app.get("/download")
async def download_video(
    url: str,
    format: str = Query("video", regex="^(video|audio)$")
):
    try:
        yt = YouTube(url)
        unique_id = str(uuid.uuid4())

        if format == "audio":
            stream = yt.streams.filter(only_audio=True).first()
            file_path = stream.download(filename=f"{unique_id}.mp4")
            base, ext = os.path.splitext(file_path)
            new_file_path = f"{base}.mp3"
            os.rename(file_path, new_file_path)
            file_path = new_file_path
        else:
            stream = yt.streams.get_highest_resolution()
            file_path = stream.download(filename=f"{unique_id}.mp4")

        # Schedule file deletion after 10 minutes
        Timer(600, lambda: os.remove(file_path) if os.path.exists(file_path) else None).start()

        return {
            "message": f"{format.capitalize()} downloaded successfully!",
            "filename": os.path.basename(file_path)
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error downloading: {str(e)}")
