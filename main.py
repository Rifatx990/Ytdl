import re
import os
import asyncio
import uuid
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from playwright.async_api import async_playwright
import requests

app = FastAPI()

YOUTUBE_API_KEY = "AIzaSyDYFu-jPat_hxdssXEK4y2QmCOkefEGnso"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
             "(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def extract_video_id(url: str) -> str | None:
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else None

def check_youtube_video(video_id: str) -> bool:
    url = f"https://www.googleapis.com/youtube/v3/videos?part=status&id={video_id}&key={YOUTUBE_API_KEY}"
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        data = resp.json()
        if "items" in data and len(data["items"]) > 0:
            status = data["items"][0]["status"]
            return status.get("uploadStatus") == "processed"
        return False
    except Exception as e:
        print(f"API error: {e}")
        return False

async def fetch_and_download(video_url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=USER_AGENT)
        await page.goto(video_url)
        await page.wait_for_selector("video")

        video_tag = await page.query_selector("video")
        stream_url = await video_tag.get_attribute("src")

        await browser.close()

        if stream_url:
            filename = f"{uuid.uuid4().hex}.mp4"
            filepath = os.path.join(DOWNLOAD_DIR, filename)
            r = requests.get(stream_url, stream=True, headers={"User-Agent": USER_AGENT})
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            asyncio.create_task(delete_file_later(filepath, 600))  # 600 seconds = 10 min
            return filepath
        else:
            raise HTTPException(status_code=404, detail="Unable to extract video stream URL")

async def delete_file_later(path: str, delay: int):
    await asyncio.sleep(delay)
    try:
        os.remove(path)
        print(f"Deleted: {path}")
    except Exception as e:
        print(f"Failed to delete {path}: {e}")

@app.get("/stream")
async def get_stream(url: str = Query(..., description="YouTube video URL")):
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube link or ID")

    if not check_youtube_video(video_id):
        raise HTTPException(status_code=404, detail="Video not available")

    try:
        file_path = await fetch_and_download(url)
        return FileResponse(file_path, media_type="video/mp4", filename=os.path.basename(file_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process video: {str(e)}")
