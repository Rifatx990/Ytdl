import os
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from playwright.async_api import async_playwright
import asyncio

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "API is running"}

@app.get("/video")
async def extract_video_stream(url: str = Query(..., description="Video URL")):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url)
            title = await page.title()
            await browser.close()
            return {"title": title}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Failed to extract stream: {e}"})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
