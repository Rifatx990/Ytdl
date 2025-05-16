from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
import subprocess
import os
import threading
import time
import uuid

app = FastAPI()

COOKIES_FILE = "cookies.txt"  # Must be placed in the root directory

def delete_file_later(filepath: str, delay: int = 600):
    def _delete():
        time.sleep(delay)
        if os.path.exists(filepath):
            os.remove(filepath)
    threading.Thread(target=_delete).start()

@app.get("/")
def root():
    return {"message": "YouTube Downloader API is live."}

@app.get("/download")
def download(
    url: str = Query(..., description="YouTube video URL"),
    format: str = Query("video", enum=["video", "audio"], description="Download format: video or audio")
):
    try:
        if not os.path.exists(COOKIES_FILE):
            raise HTTPException(status_code=500, detail="Missing cookies.txt file in root directory.")

        ext = "mp4" if format == "video" else "mp3"
        out_name = f"{uuid.uuid4()}.{ext}"

        ytdlp_cmd = [
            "yt-dlp",
            "--cookies", COOKIES_FILE,
            "-f", "best" if format == "video" else "bestaudio",
            "-o", out_name,
            url
        ]

        subprocess.run(ytdlp_cmd, check=True)

        delete_file_later(out_name)

        return FileResponse(out_name, media_type="application/octet-stream", filename=out_name)

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=400, detail=f"Download failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {e}")
