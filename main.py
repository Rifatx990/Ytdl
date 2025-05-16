from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
import subprocess
import os
import uuid
import asyncio

app = FastAPI()

COOKIE_FILE = "cookies.txt"  # Your cookies file in the same directory

async def delete_file_later(file_path: str, delay_sec: int = 600):
    await asyncio.sleep(delay_sec)
    if os.path.exists(file_path):
        os.remove(file_path)

@app.get("/download")
async def download_media(url: str = Query(...), format: str = Query("video", regex="^(video|audio)$")):
    try:
        output_id = str(uuid.uuid4())
        output_template = f"{output_id}.%(ext)s"

        cmd = [
            "yt-dlp",
            "--no-warnings",
            "--cookies", COOKIE_FILE,
            "-o", output_template,
            url
        ]

        if format == "audio":
            cmd.extend(["-f", "bestaudio"])
        else:
            cmd.extend(["-f", "bestvideo+bestaudio/best"])

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if proc.returncode != 0:
            raise HTTPException(status_code=400, detail=f"DownloadError: {proc.stderr.strip()}")

        downloaded_file = None
        for file in os.listdir():
            if file.startswith(output_id):
                downloaded_file = file
                break

        if not downloaded_file or not os.path.exists(downloaded_file):
            raise HTTPException(status_code=500, detail="Download failed; file missing.")

        asyncio.create_task(delete_file_later(downloaded_file))

        media_type = "audio/mpeg" if format == "audio" else "video/mp4"
        return FileResponse(downloaded_file, media_type=media_type, filename=downloaded_file)

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Download process timed out.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error downloading: {str(e)}")
