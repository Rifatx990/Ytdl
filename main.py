from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import yt_dlp
import os
import logging

app = FastAPI()

# Path to your cookies.txt (should be in same directory or specify full path)
COOKIES_PATH = os.path.join(os.path.dirname(__file__), 'cookies.txt')

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.get("/downloads")
async def download_video(url: str = Query(..., description="YouTube video URL")):
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'nocheckcertificate': True,
        'cookies': COOKIES_PATH,
        'skip_download': True,  # If you want metadata only, change as needed
        # 'outtmpl': 'downloads/%(title)s.%(ext)s',  # for actual download path
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)  # download=False uses metadata only
            # Optionally, you could download by setting download=True and removing skip_download
            return JSONResponse(content={
                "title": info.get("title"),
                "id": info.get("id"),
                "uploader": info.get("uploader"),
                "duration": info.get("duration"),
                "webpage_url": info.get("webpage_url"),
            })
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"DownloadError: {str(e)}")
        raise HTTPException(status_code=400, detail=f"DownloadError: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
