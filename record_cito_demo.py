#!/usr/bin/env python3
"""Regenerate Cito_Demo.mp4 from the real interface (not a separate mockup).

Requires: pip install playwright imageio-ffmpeg && python -m playwright install chromium

Drives index.html with the same buttons a presenter would click, records the
session at 1920x1080, and encodes the result to Cito_Demo.mp4 at 30 fps with
no audio. Run from inside this folder: python record_cito_demo.py

A small cursor is drawn on top of the page for the recording only (it is
injected at runtime and is never part of the shipped app) so the video shows
where each click lands and how the pointer moves between them.

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

# Recording-only cursor overlay: a positioned wrapper (smooth transform
# transition) holding an SVG pointer (separate opacity/scale for the
# press feedback). Never touches the shipped app files.
INIT_CURSOR_JS = """
() => {
  if (document.getElementById('__demo_cursor_pos')) return;
  const pos = document.createElement('div');
  pos.id = '__demo_cursor_pos';
  pos.style.cssText = 'position:fixed;left:0;top:0;width:0;height:0;'
    + 'z-index:2147483647;pointer-events:none;'
    + 'transition:transform .62s cubic-bezier(.45,.05,.3,1);'
    + 'transform:translate(-100px,-100px);';
  const dot = document.createElement('div');
  dot.id = '__demo_cursor_dot';
  dot.style.cssText = 'position:absolute;left:-3px;top:-2px;opacity:0;'
    + 'transition:opacity .2s ease,transform .15s ease;'
    + 'filter:drop-shadow(0 1px 2px rgba(0,0,0,.35));';
  dot.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24">'
    + '<path d="M4 2l16 11-7 1.5L9.5 22z" fill="#12395B" stroke="#fff" '
    + 'stroke-width="1.6" stroke-linejoin="round"/></svg>';
  pos.appendChild(dot);
  document.body.appendChild(pos);
}
"""


def init_cursor(page):
    page.evaluate(INIT_CURSOR_JS)


def move_cursor_to(page, selector):
    """Slide the overlay cursor to the centre of `selector` and return its box."""
    box = page.eval_on_selector(
        selector,
        "el => { const r = el.getBoundingClientRect();"
        " return {x: r.left + r.width/2, y: r.top + r.height/2}; }",
    )
    page.evaluate(
        "([x, y]) => {"
        " document.getElementById('__demo_cursor_dot').style.opacity = '1';"
        " document.getElementById('__demo_cursor_pos').style.transform ="
        "   `translate(${x}px, ${y}px)`;"
        "}",
        [box["x"], box["y"]],
    )
    return box


def press_pulse(page):
    page.evaluate(
        "() => {"
        " const dot = document.getElementById('__demo_cursor_dot');"
        " dot.style.transform = 'scale(0.8)';"
        " setTimeout(() => { dot.style.transform = 'scale(1)'; }, 140);"
        "}"
    )


def hide_cursor(page):
    page.evaluate(
        "() => {"
        " const dot = document.getElementById('__demo_cursor_dot');"
        " if (dot) dot.style.opacity = '0';"
        "}"
    )


def click_with_cursor(page, selector, travel_ms=700, settle_ms=250):
    """Move the visible cursor to `selector`, show a press, then really click it."""
    move_cursor_to(page, selector)
    page.wait_for_timeout(travel_ms)
    press_pulse(page)
    page.wait_for_timeout(settle_ms)
    page.click(selector)


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
    init_cursor(page)
    page.wait_for_timeout(1600)
    lead = time.time() - t0

    # 1. Patient record — hold so the timeline and work item are readable
    page.wait_for_timeout(3600)

    # 2. Open the hospital discharge report for review
    click_with_cursor(page, "#openDoc")
    page.wait_for_timeout(3000)

    # expand the collapsed medication detail
    click_with_cursor(page, "#medToggle")
    page.wait_for_timeout(2200)

    # 3. Open and highlight the supporting source sentence
    click_with_cursor(page, '[data-source="s-fu1 s-fu2"]')
    page.wait_for_timeout(3400)

    # 4. Verify the fields
    click_with_cursor(page, "#verifyBtn")
    page.wait_for_timeout(2800)

    # record GP follow-up
    click_with_cursor(page, "#continueBtn")
    page.wait_for_timeout(2800)

    # 5. Generate the COPD overview
    click_with_cursor(page, "#createBtn")
    page.wait_for_timeout(2600)
    move_cursor_to(page, "#view-overview")
    page.mouse.wheel(0, 260)  # reveal the medication / recommendations section
    page.wait_for_timeout(2200)

    # save to record, then hold the completed overview
    click_with_cursor(page, "#saveBtn")
    page.wait_for_timeout(1600)
    hide_cursor(page)             # keep the final held frame clean
    page.wait_for_timeout(2600)

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
