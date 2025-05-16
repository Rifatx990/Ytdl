from fastapi import FastAPI, HTTPException, Query
import yt_dlp
import requests

app = FastAPI()

YOUTUBE_API_KEY = "AIzaSyDYFu-jPat_hxdssXEK4y2QmCOkefEGnso"

def verify_youtube_video(video_id: str):
    url = f"https://www.googleapis.com/youtube/v3/videos?part=status&id={video_id}&key={YOUTUBE_API_KEY}"
    response = requests.get(url).json()
    if response.get("pageInfo", {}).get("totalResults", 0) == 0:
        return False
    return True

def search_youtube(query: str):
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=1&q={query}&key={YOUTUBE_API_KEY}"
    response = requests.get(url).json()
    items = response.get("items", [])
    if not items:
        return None
    video_id = items[0]["id"]["videoId"]
    return f"https://youtu.be/{video_id}"

def extract_video_id(url: str):
    # Basic extraction for YouTube video ID from URL
    import re
    patterns = [
        r"youtu\.be\/([^?&]+)",
        r"v=([^?&]+)",
        r"\/embed\/([^?&]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@app.get("/downloads")
async def download_video(url: str = Query(..., description="YouTube video URL or search query")):
    video_id = extract_video_id(url)
    if video_id:
        valid = verify_youtube_video(video_id)
        if not valid:
            # If video ID invalid, treat URL param as search query
            search_url = search_youtube(url)
            if not search_url:
                raise HTTPException(status_code=404, detail="No video found matching the query")
            url = search_url
    else:
        # url param is probably a search query, not a direct URL
        search_url = search_youtube(url)
        if not search_url:
            raise HTTPException(status_code=404, detail="No video found matching the query")
        url = search_url

    # Use yt-dlp with cookies.txt for download/info
    ydl_opts = {
        'cookiefile': './cookies.txt',
        'quiet': True,
        'skip_download': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title"),
                "id": info.get("id"),
                "uploader": info.get("uploader"),
                "duration": info.get("duration"),
                "webpage_url": info.get("webpage_url"),
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"DownloadError: {str(e)}")
