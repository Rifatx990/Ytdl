import os
import uuid
import asyncio
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.get("/")
async def root():
    return {"message": "YouTube Downloader API is live."}

@app.get("/download")
async def download_video(url: str = Query(...), format: str = Query("video")):
    file_ext = "mp4" if format == "video" else "mp3"
    unique_id = str(uuid.uuid4())
    filename = os.path.join(DOWNLOAD_DIR, f"{unique_id}.{file_ext}")

    ydl_opts = {
        "outtmpl": filename,
        "format": "bestaudio/best" if format == "audio" else "bestvideo+bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "merge_output_format": "mp4" if format == "video" else "mp3",
        "cookies": "cookies.txt" if os.path.exists("cookies.txt") else None,
        "postprocessors": [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }] if format == "audio" else [],
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except DownloadError as e:
        raise HTTPException(status_code=400, detail=f"DownloadError: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    # Schedule file deletion in 10 minutes
    asyncio.create_task(delete_file_later(filename, 600))

    return FileResponse(
        path=filename,
        filename=info.get("title", unique_id) + f".{file_ext}",
        media_type="application/octet-stream"
    )

async def delete_file_later(path: str, delay: int):
    await asyncio.sleep(delay)
    if os.path.exists(path):
        os.remove(path)
