import os
import uuid
import asyncio
import logging
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

app = FastAPI()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("yt-downloader")

@app.get("/")
async def root():
    return {"message": "YouTube Downloader API is live."}

@app.get("/download")
async def download_video(url: str = Query(..., description="YouTube video URL"), 
                         format: str = Query("video", regex="^(video|audio)$", description="Format: video or audio")):
    unique_id = str(uuid.uuid4())
    file_ext = "mp4" if format == "video" else "mp3"
    output_path = os.path.join(DOWNLOAD_DIR, f"{unique_id}.%(ext)s")

    # yt-dlp options
    ydl_opts = {
        "outtmpl": output_path,
        "format": "bestaudio/best" if format == "audio" else "bestvideo+bestaudio/best",
        "quiet": True,
        "noplaylist": True,
        "merge_output_format": "mp4" if format == "video" else None,
        "postprocessors": [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }] if format == "audio" else [],
        "cookies": "cookies.txt" if os.path.exists("cookies.txt") else None,
        "nocheckcertificate": True,
    }

    logger.info(f"Starting download for url={url} format={format}")

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        # Get actual filename with extension
        ext = info.get('ext', file_ext)
        final_file = os.path.join(DOWNLOAD_DIR, f"{unique_id}.{ext}")
        logger.info(f"Downloaded file: {final_file}")

    except DownloadError as e:
        logger.error(f"DownloadError: {e}")
        raise HTTPException(status_code=400, detail=f"DownloadError: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    # Schedule deletion after 10 minutes
    asyncio.create_task(delete_file_later(final_file, 600))

    # Send file with original video title as filename (sanitize)
    safe_title = "".join(c if c.isalnum() or c in " -_." else "_" for c in info.get("title", unique_id))
    send_filename = f"{safe_title}.{ext}"

    return FileResponse(
        path=final_file,
        filename=send_filename,
        media_type="application/octet-stream",
    )

async def delete_file_later(path: str, delay: int):
    logger.info(f"Scheduling deletion of {path} in {delay} seconds")
    await asyncio.sleep(delay)
    if os.path.exists(path):
        try:
            os.remove(path)
            logger.info(f"Deleted file: {path}")
        except Exception as e:
            logger.error(f"Error deleting file {path}: {e}")
