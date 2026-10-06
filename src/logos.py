"""Download the logos for the deck: the three app icons from their Play Store listings, and the Google Play logo.

Writes data/logos/*.png. They are the companies' trademarks, so they stay out of git (data/ is ignored).
"""
import json
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from google_play_scraper import app
from PIL import Image, ImageDraw

from pull_reviews import APPS

OUT = Path(__file__).resolve().parents[1] / "data" / "logos"
HEADERS = {"User-Agent": "qc-nps-portfolio/1.0"}
COMMONS = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
    {"action": "query", "titles": "File:Google_Play_2022_icon.svg", "prop": "imageinfo", "iiprop": "url",
     "iiurlwidth": 512, "format": "json"})


def get(url: str) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30).read()


def rounded(img: Image.Image) -> Image.Image:
    """Square icon with rounded corners, the way it shows on a phone."""
    img = img.convert("RGBA").resize((512, 512))
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 511, 511), radius=112, fill=255)
    img.putalpha(mask)
    return img


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, pid in APPS.items():
        icon = app(pid, lang="en", country="in")["icon"].split("=")[0] + "=s512"
        rounded(Image.open(BytesIO(get(icon)))).save(OUT / f"{name}.png")
    page = next(iter(json.loads(get(COMMONS))["query"]["pages"].values()))
    Image.open(BytesIO(get(page["imageinfo"][0]["thumburl"]))).convert("RGBA").save(OUT / "googleplay.png")
    print(*sorted(p.name for p in OUT.glob("*.png")), sep="\n")
