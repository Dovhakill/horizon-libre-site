import os
import sys
import json
import hashlib
import time
import subprocess
from io import BytesIO
from typing import List, Tuple, Optional

import requests
import tweepy
from bs4 import BeautifulSoup
from PIL import Image

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Constants
SITE_URL = "https://horizon-libre.net"
ARTICLES_DIR = "article"
MAX_TWEET_LENGTH = 280
UTM_PARAMS = "?utm_source=twitter&utm_medium=social&utm_campaign=autotweet"
GEMINI_MODEL_DEFAULT = "gemini-1.5-flash"
PAUSE_BETWEEN_TWEETS = 10  # seconds
EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
MAX_ARTICLES_PER_RUN = 5  # limit per run

HTTP_TIMEOUT = 15
REQUESTS_HEADERS = {"User-Agent": "horizon-libre-autotweet/1.0"}

def log(message: str) -> None:
    print(message, flush=True)

# Dedup memory
def get_memory_key(article_path: str) -> str:
    return hashlib.sha256(article_path.encode()).hexdigest().lower()

def has_been_seen(key: str, blobs_url: Optional[str], token: Optional[str]) -> bool:
    if not blobs_url or not token:
        return False
    try:
        url = f"{blobs_url.rstrip('/')}/{key}"
        r = requests.get(url, headers={"X-AURORE-TOKEN": token, **REQUESTS_HEADERS}, timeout=HTTP_TIMEOUT)
        return r.status_code == 200
    except Exception as e:
        log(f"Memory check failed: {e}")
        return False

def mark_as_seen(key: str, blobs_url: Optional[str], token: Optional[str]) -> None:
    if not blobs_url or not token:
        return
    try:
        url = f"{blobs_url.rstrip('/')}/{key}"
        requests.put(url, data="1", headers={"X-AURORE-TOKEN": token, **REQUESTS_HEADERS}, timeout=HTTP_TIMEOUT)
    except Exception as e:
        log(f"Memory mark failed: {e}")

# Read GitHub event
def read_github_event() -> Optional[dict]:
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"Failed to read event file: {e}")
        return None

def _normalize_articles_list(raw) -> List[str]:
    # Accept ["article/a.html", ...] or [{"path": "article/a.html"}, ...]
    paths: List[str] = []
    if isinstance(raw, list):
        for it in raw:
            if isinstance(it, str):
                paths.append(it)
            elif isinstance(it, dict) and "path" in it and isinstance(it["path"], str):
                paths.append(it["path"])
    return paths

# Detect new articles
def detect_new_articles() -> List[str]:
    event = read_github_event()
    event_name = os.environ.get("GITHUB_EVENT_NAME")

    # repository_dispatch path
    if event_name == "repository_dispatch" and event and event.get("action") == "new-article-published":
        payload = event.get("client_payload", {}) or {}
        arts = _normalize_articles_list(payload.get("articles", []))
        arts = [a for a in arts if isinstance(a, str) and a.startswith(f"{ARTICLES_DIR}/") and a.endswith(".html")]
        return arts[:MAX_ARTICLES_PER_RUN]

    # optional: push path (not used if on: push est retiré du workflow)
    if event_name == "push" and event:
        before = event.get("before")
        after = event.get("after")
        try:
            if before and after:
                diff_output = subprocess.check_output(
                    ["git", "diff", "--diff-filter=A", "--name-only", before, after],
                    text=True
                ).splitlines()
            else:
                # fallback if before/after not present
                try:
                    prev_sha = subprocess.check_output(["git", "rev-parse", "HEAD~1"], text=True).strip()
                except subprocess.CalledProcessError:
                    prev_sha = EMPTY_TREE_SHA
                diff_output = subprocess.check_output(
                    ["git", "diff", "--diff-filter=A", "--name-only", prev_sha, "HEAD"],
                    text=True
                ).splitlines()
            arts = [f for f in diff_output if f.startswith(f"{ARTICLES_DIR}/") and f.endswith(".html")]
            return arts[:MAX_ARTICLES_PER_RUN]
        except Exception as e:
            log(f"Git diff failed: {e}")
            return []

    # default: nothing
    return []

# Parse HTML
def parse_article(article_path: str) -> Tuple[Optional[str], Optional[str], Optional[BeautifulSoup]]:
    try:
        with open(article_path, "r", encoding="utf-8") as f:
            html = f.read()
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"
        category = None
        meta_section = soup.find("meta", {"property": "article:section"})
        if meta_section and meta_section.get("content"):
            category = meta_section["content"].strip()
        else:
            meta_category = soup.find("meta", {"name": "category"})
            if meta_category and meta_category.get("content"):
                category = meta_category["content"].strip()
        return title, category, soup
    except Exception as e:
        log(f"Parsing failed for {article_path}: {e}")
        return None, None, None

def generate_hashtags(title: Optional[str], category: Optional[str]) -> str:
    hashtags = ["#HorizonLibre"]
    if category:
        hashtags.append(f"#{category.replace(' ', '').lower()}")
    elif title:
        words = title.split()
        if words:
            hashtags.append(f"#{words[0].lower()}")
    # Max 2 tags
    tags = list(dict.fromkeys(hashtags))[:2]
    return " ".join(tags)

def _is_truthy_env(name: str) -> bool:
    val = os.environ.get(name, "")
    return str(val).strip().lower() in ("1", "true", "yes", "on")

def append_utm(url: str) -> str:
    return url + UTM_PARAMS if _is_truthy_env("ENABLE_UTM") else url

def safe_trim(text: str, max_len: int = MAX_TWEET_LENGTH) -> str:
    return text if len(text) <= max_len else (text[: max_len - 3] + "...")

def generate_alt_text(image_data: Optional[bytes], gemini_api_key: Optional[str], gemini_model: str) -> str:
    if not image_data:
        return "Image from article"
    if gemini_api_key and genai:
        try:
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel(gemini_model)
            resp = model.generate_content(["Describe this image briefly for accessibility.", image_data])
            alt = (resp.text or "").strip()[:1000]
            return alt if alt else "Image from article"
        except Exception as e:
            log(f"Gemini failed: {e}")
    return "Image from article"

def _read_local_image_bytes(article_path: str, img_url: str) -> Optional[bytes]:
    # Handle absolute site path (/images/x.jpg) vs relative (x.jpg or ./x.jpg or subdir/x.jpg)
    if img_url.startswith("/"):
        local_rel = img_url.lstrip("/")  # path relative to repo root
    else:
        local_rel = os.path.normpath(os.path.join(os.path.dirname(article_path), img_url))
    if not os.path.exists(local_rel):
        log(f"Local image not found: {local_rel}")
        return None
    try:
        with open(local_rel, "rb") as f:
            return f.read()
    except Exception as e:
        log(f"Failed to read local image {local_rel}: {e}")
        return None

def find_and_prepare_image(article_path: str, soup: BeautifulSoup) -> Tuple[Optional[bytes], Optional[str]]:
    try:
        img_url = None
        alt = None

        og_image = soup.find("meta", {"property": "og:image"})
        if og_image and og_image.get("content"):
            img_url = og_image["content"].strip()
        elif (tw := soup.find("meta", {"name": "twitter:image"})) and tw.get("content"):
            img_url = tw["content"].strip()
        elif (ln := soup.find("link", {"rel": "image_src"})) and ln.get("href"):
            img_url = ln["href"].strip()
        else:
            article_tag = soup.find("article")
            if article_tag:
                img_tag = article_tag.find("img")
                if img_tag and img_tag.get("src"):
                    img_url = img_tag["src"].strip()
                    if img_tag.get("alt"):
                        alt = img_tag["alt"].strip()
                    else:
                        fig = img_tag.find_parent("figure")
                        if fig:
                            cap = fig.find("figcaption")
                            if cap and cap.text:
                                alt = cap.text.strip()

        if not img_url:
            return None, None

        if img_url.startswith("http://") or img_url.startswith("https://"):
            r = requests.get(img_url, headers=REQUESTS_HEADERS, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            img_data = r.content
        else:
            img_data = _read_local_image_bytes(article_path, img_url)
            if not img_data:
                return None, None

        img = Image.open(BytesIO(img_data)).convert("RGB")

        # Resize if too large
        max_size = 4096
        if img.width > max_size or img.height > max_size:
            ratio = min(max_size / img.width, max_size / img.height)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)

        # Compress until under ~4.8MB or quality 50
        quality = 95
        while True:
            buffer = BytesIO()
            img.save(buffer, format="JPEG", progressive=True, quality=quality)
            size = buffer.tell()
            if size <= int(4.8 * 1024 * 1024) or quality <= 50:
                break
            quality -= 5

        return buffer.getvalue(), alt
    except Exception as e:
        log(f"Image processing failed: {e}")
        return None, None

def build_tweet_text(title: str, hashtags: str, article_url: str) -> str:
    base = f"Nouvel article: {title}"
    tweet = f"{base} {hashtags} {article_url}"
    return safe_trim(tweet)

def post_tweet(tweet_text: str, image_data: Optional[bytes] = None, alt_text: Optional[str] = None) -> None:
    try:
        consumer_key = os.environ["X_API_KEY"]
        consumer_secret = os.environ["X_API_SECRET"]
        access_token = os.environ["X_ACCESS_TOKEN"]
        access_token_secret = os.environ["X_ACCESS_TOKEN_SECRET"]

        # v1.1 for media upload
        auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
        api_v1 = tweepy.API(auth)

        # v2 for posting tweet
        client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )

        media_ids = None
        if image_data:
            media = api_v1.media_upload(filename="image.jpg", file=BytesIO(image_data))
            media_ids = [media.media_id]
            if alt_text:
                try:
                    api_v1.create_media_metadata(media.media_id, alt_text)
                except Exception as e:
                    log(f"Alt text set failed: {e}")

        client.create_tweet(text=tweet_text, media_ids=media_ids)
        log("Tweet posted successfully")
    except Exception as e:
        log(f"Tweet posting failed: {e}")

def main() -> None:
    articles = detect_new_articles()
    if not articles:
        log("No new articles found")
        return

    log(f"Articles to process: {articles}")

    blobs_url = os.environ.get("BLOBS_PROXY_URL")
    aurore_token = os.environ.get("AURORE_BLOBS_TOKEN")
    gemini_api_key = os.environ.get("GEMINI_API_KEY_HORIZON")
    gemini_model = os.environ.get("GEMINI_MODEL", GEMINI_MODEL_DEFAULT)

    for idx, article_path in enumerate(articles):
        key = get_memory_key(article_path)
        if has_been_seen(key, blobs_url, aurore_token):
            log(f"Skipping duplicate: {article_path}")
            continue

        title, category, soup = parse_article(article_path)
        if not title or not soup:
            log(f"Skipping invalid article: {article_path}")
            continue

        hashtags = generate_hashtags(title, category)
        article_url = append_utm(f"{SITE_URL}/{article_path}")
        tweet_text = build_tweet_text(title, hashtags, article_url)

        image_data, html_alt = find_and_prepare_image(article_path, soup)
        alt_text = html_alt if html_alt else (generate_alt_text(image_data, gemini_api_key, gemini_model) if image_data else None)

        post_tweet(tweet_text, image_data, alt_text)
        mark_as_seen(key, blobs_url, aurore_token)

        if idx < len(articles) - 1:
            time.sleep(PAUSE_BETWEEN_TWEETS)

if __name__ == "__main__":
    main()
