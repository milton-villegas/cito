#!/usr/bin/env python3
"""Regenerate Cito_Demo.mp4 from the real interface (not a separate mockup).

Requires: pip install playwright imageio-ffmpeg && python -m playwright install chromium

Drives index.html with the same buttons a presenter would click, records the
session at 1920x1080, and encodes the result to Cito_Demo.mp4 at 30 fps with
no audio. Run from inside this folder: python record_cito_demo.py

Note (macOS): the recording is written to a system temp directory rather
than into this folder. On macOS, ~/Documents (and similar folders) are
protected by TCC, and Chromium's video encoder can silently write 0-byte
files there even though the shell and ffmpeg can read/write it fine.
"""
import glob
import os
import shutil
import subprocess
import tempfile
import time

from playwright.sync_api import sync_playwright
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "index.html")
OUT_MP4 = os.path.join(HERE, "Cito_Demo.mp4")
VIDEO_DIR = tempfile.mkdtemp(prefix="cito_record_")

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        record_video_dir=VIDEO_DIR,
        record_video_size={"width": 1920, "height": 1080},
    )
    t0 = time.time()
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("file://" + INDEX)
    page.wait_for_timeout(1600)
    lead = time.time() - t0

    # 1. Patient record — hold so the timeline and work item are readable
    page.wait_for_timeout(4500)

    # 2. Open the hospital discharge report for review
    page.click("#openDoc")
    page.wait_for_timeout(3500)

    # expand the collapsed medication detail
    page.click("#medToggle")
    page.wait_for_timeout(2600)

    # 3. Open and highlight the supporting source sentence
    page.click('[data-source="s-fu1 s-fu2"]')
    page.wait_for_timeout(3800)

    # 4. Verify the fields
    page.click("#verifyBtn")
    page.wait_for_timeout(3200)

    # record GP follow-up
    page.click("#continueBtn")
    page.wait_for_timeout(3200)

    # 5. Generate the COPD overview
    page.click("#createBtn")
    page.wait_for_timeout(3200)
    page.mouse.wheel(0, 260)  # reveal the medication / recommendations section
    page.wait_for_timeout(2600)

    # save to record, then hold the completed overview
    page.click("#saveBtn")
    page.wait_for_timeout(4200)

    if errors:
        print("WARNING - console errors during recording:", errors)

    page.close()
    ctx.close()
    browser.close()

webm = glob.glob(os.path.join(VIDEO_DIR, "*.webm"))[0]
if os.path.getsize(webm) == 0:
    raise SystemExit(
        "Recorded video is empty. On macOS this usually means the recording "
        "directory is under a TCC-protected folder (Documents, Desktop, "
        "Downloads). Set VIDEO_DIR to a path under /tmp instead."
    )

ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
cmd = [
    ffmpeg, "-y",
    "-ss", f"{max(lead - 0.2, 0):.2f}",
    "-i", webm,
    "-an",
    "-r", "30",
    "-fps_mode", "cfr",
    "-vf", "scale=1920:1080",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "slow", "-crf", "18",
    "-movflags", "+faststart",
    OUT_MP4,
]
result = subprocess.run(cmd, capture_output=True, text=True)
shutil.rmtree(VIDEO_DIR, ignore_errors=True)

if result.returncode != 0:
    raise SystemExit("ffmpeg failed:\n" + result.stderr[-2000:])
print("Wrote", OUT_MP4)
