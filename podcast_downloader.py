# Podcast Downloader Script
# Usage examples:
#   Top 5 newest:           python podcast_downloader.py "https://your-feed.xml" -t 5
#   Specific by title:      python podcast_downloader.py "https://your-feed.xml" -e "funny cats"
#   Specific by number:     python podcast_downloader.py "https://your-feed.xml" -n 42

import feedparser
import requests
import os
import sys
import re
import argparse

def sanitize_filename(name: str) -> str:
    if not name:
        return "unknown"
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:180]

# ------------------------------
# Command-line arguments
# ------------------------------
parser = argparse.ArgumentParser(description="Download podcast episodes from RSS feed")
parser.add_argument("rss_url", help="The RSS feed URL")
parser.add_argument("-e", "--episode", type=str, default=None,
                    help="Partial episode title to match (case-insensitive)")
parser.add_argument("-n", "--number", type=int, default=None,
                    help="Exact episode number to download")
parser.add_argument("-t", "--top", type=int, default=10,
                    help="Number of newest episodes to download when no specific episode/number is given (default: 10)")
args = parser.parse_args()

rss_url = args.rss_url
search_title = args.episode
target_number = args.number
top_count = max(1, min(args.top, 100))  # sensible limits: 1–100

if target_number is not None and search_title is not None:
    print("ℹ️  Both --number and --episode provided → --number takes priority")
if target_number is not None or search_title is not None:
    print(f"ℹ️  Specific episode requested → ignoring --top ({top_count})")

print(f"📡 Fetching RSS feed: {rss_url}")
feed = feedparser.parse(rss_url)

if not feed.entries:
    print("❌ No episodes found in the feed.")
    sys.exit(1)

# Podcast folder
podcast_title = sanitize_filename(feed.feed.get("title", "Podcast"))
download_dir = os.path.join(os.getcwd(), podcast_title)
os.makedirs(download_dir, exist_ok=True)
print(f"📁 Saving to: {download_dir}")

# Helper to get episode number
def get_episode_number(entry):
    if hasattr(entry, "itunes_episode") and entry.itunes_episode:
        try:
            return int(entry.itunes_episode)
        except:
            pass
    title = entry.get("title", "")
    match = re.search(r'(?:ep(?:isode|\.)?|#)?\s*(\d{1,4})\b', title, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

# Select episodes to process
episodes = []

if target_number is not None:
    for entry in feed.entries:
        if get_episode_number(entry) == target_number:
            episodes.append(entry)
            break
    if not episodes:
        print(f"❌ No episode found with number {target_number}")
        sys.exit(1)
    print(f"🎯 Found episode #{target_number}: {episodes[0].get('title', 'Untitled')}")

elif search_title:
    search_lower = search_title.lower()
    for entry in feed.entries:
        if search_lower in entry.get("title", "").lower():
            episodes.append(entry)
            break
    if not episodes:
        print(f"❌ No episode found containing: '{search_title}'")
        sys.exit(1)
    print(f"🎯 Found matching episode: {episodes[0].get('title', 'Untitled')}")

else:
    # Default mode: top N newest
    episodes = feed.entries[:top_count]
    print(f"📥 Downloading top {len(episodes)} newest episode{'s' if len(episodes) != 1 else ''}")

# Process selected episodes
for idx, entry in enumerate(episodes, 1):
    title = entry.get("title", f"Episode {idx}").strip()
    
    ep_num = get_episode_number(entry)
    ep_num_str = f"{ep_num:03d}" if ep_num is not None else f"{idx:03d}"
    
    # Clean name, remove number prefix if present
    episode_name = re.sub(r'^(?:ep(?:isode|\.)?|#)?\s*\d+\s*[-:–]\s*', '', title, flags=re.IGNORECASE)
    episode_name = sanitize_filename(episode_name or "Untitled")
    
    base_name = f"{ep_num_str}_{episode_name}"
    
    print(f"🎙️  Processing: {base_name}")
    
    # Audio
    audio_url = None
    if entry.get("enclosures"):
        for enc in entry.enclosures:
            href = enc.get("href")
            if not href: continue
            typ = enc.get("type", "").lower()
            if typ.startswith("audio/") or href.lower().endswith((".mp3", ".m4a", ".ogg", ".aac")):
                audio_url = href
                break
    
    if audio_url:
        audio_path = os.path.join(download_dir, f"{base_name}.mp3")
        if not os.path.exists(audio_path):
            print(f"   ⬇️  Downloading audio...")
            try:
                r = requests.get(audio_url, stream=True, timeout=30)
                r.raise_for_status()
                with open(audio_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        f.write(chunk)
                print(f"   ✅ Audio saved: {base_name}.mp3")
            except Exception as e:
                print(f"   ❌ Audio failed: {e}")
        else:
            print(f"   ⏭️  Audio already exists")
    else:
        print(f"   ⚠️  No audio found")
    
    # Image
    image_url = None
    if hasattr(entry, "itunes_image") and entry.itunes_image and "href" in entry.itunes_image:
        image_url = entry.itunes_image["href"]
    elif entry.get("image"):
        image_url = entry.image.get("href") if isinstance(entry.image, dict) else entry.image
    
    if not image_url and hasattr(feed.feed, "itunes_image") and feed.feed.itunes_image and "href" in feed.feed.itunes_image:
        image_url = feed.feed.itunes_image["href"]
    elif not image_url and feed.feed.get("image"):
        image_url = feed.feed.image.get("href") if isinstance(feed.feed.image, dict) else feed.feed.image.get("url")
    
    if image_url:
        try:
            r = requests.get(image_url, stream=True, timeout=15)
            r.raise_for_status()
            content_type = r.headers.get("content-type", "").lower()
            img_ext = ".png" if "png" in content_type else ".jpg"
            img_path = os.path.join(download_dir, f"{base_name}{img_ext}")
            
            if not os.path.exists(img_path):
                print(f"   ⬇️  Downloading image...")
                with open(img_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        f.write(chunk)
                print(f"   ✅ Image saved: {base_name}{img_ext}")
            else:
                print(f"   ⏭️  Image already exists")
        except Exception as e:
            print(f"   ❌ Image failed: {e}")
    else:
        print(f"   ⚠️  No image found")

print("\n🎉 Done!")
print(f"📂 Folder: {download_dir}")
