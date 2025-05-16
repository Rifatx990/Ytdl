from fastapi import FastAPI, HTTPException, Query
from yt_dlp import YoutubeDL
import requests
import logging

app = FastAPI()

YOUTUBE_API_KEY = "AIzaSyDYFu-jPat_hxdssXEK4y2QmCOkefEGnso"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
             "(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"

logging.basicConfig(level=logging.INFO)

def check_youtube_video(video_id: str) -> bool:
    url = f"https://www.googleapis.com/youtube/v3/videos?part=status&id={video_id}&key={YOUTUBE_API_KEY}"
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        data = resp.json()
        if "items" in data and len(data["items"]) > 0:
            status = data["items"][0]["status"]
            return status.get("uploadStatus") == "processed" and not status.get("privacyStatus") == "private"
        else:
            return False
    except Exception as e:
        logging.error(f"Error checking video with YouTube API: {e}")
        return False

def extract_video_id(url: str) -> str | None:
    # Simple extractor for youtube links (can be improved)
    import re
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",  # ?v=VIDEOID or /VIDEOID pattern
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None

@app.get("/download")
async def download_video(url: str = Query(..., description="YouTube video URL")):
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL or unable to extract video ID")

    if not check_youtube_video(video_id):
        raise HTTPException(status_code=404, detail="Video not found or unavailable")

    ydl_opts = {
        'http_headers': {'User-Agent': USER_AGENT},
        'cookiefile': 'cookies.txt',      # Use cookies.txt file from local directory
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title"),
                "uploader": info.get("uploader"),
                "duration": info.get("duration"),
                "webpage_url": info.get("webpage_url"),
                "thumbnail": info.get("thumbnail"),
                "description": info.get("description"),
            }
    except Exception as e:
        logging.error(f"yt-dlp error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing video: {str(e)}")
