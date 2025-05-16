import re
import os
import asyncio
import tempfile
from fastapi import FastAPI, HTTPException, Query
from playwright.async_api import async_playwright
import requests
from threading import Timer
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
USER_AGENT = os.getenv("USER_AGENT")

app = FastAPI()

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

async def fetch_stream_url(video_url: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=USER_AGENT)
        await page.goto(video_url, timeout=60000)
        await page.wait_for_selector("video", timeout=10000)
        video_tag = await page.query_selector("video")
        stream_url = await video_tag.get_attribute("src")
        await browser.close()

        if stream_url:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
            temp_file.write(stream_url.encode())
            temp_file.close()
            Timer(600, lambda: os.remove(temp_file.name)).start()
            return {"stream_url": stream_url, "temp_file": temp_file.name}
        else:
            raise HTTPException(status_code=404, detail="Unable to extract video stream URL")

@app.get("/stream")
async def get_stream(url: str = Query(..., description="YouTube video URL")):
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube link or ID")

    if not check_youtube_video(video_id):
        raise HTTPException(status_code=404, detail="Video not available")

    try:
        stream_data = await fetch_stream_url(url)
        return {"video_id": video_id, **stream_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract stream: {str(e)}")
