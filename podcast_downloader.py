# Podcast Downloader Script
# Now embeds downloaded episode image as album artwork (cover) in the MP3 file
#
# Usage same as before, e.g.:
#   python podcast_downloader.py "https://feed.xml" -t 5
#   python podcast_downloader.py "https://feed.xml" -n 42
#   python podcast_downloader.py "https://feed.xml" -e "funny story"
#   python podcast_downloader.py "https://feed.xml" -r 10-20 

import feedparser
import requests
import os
import sys
import re
import argparse
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC

def sanitize_filename(name: str) -> str:
    if not name:
        return "unknown"
    name = re.sub(r'[\\/*?:"<>|]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:180]

# ------------------------------
# Command-line arguments
# ------------------------------
parser = argparse.ArgumentParser(description="Download podcast episodes from RSS + embed cover art")
parser.add_argument("rss_url", help="The RSS feed URL")
parser.add_argument("-e", "--episode", type=str, default=None,
                    help="Partial episode title to match (case-insensitive)")
parser.add_argument("-n", "--number", type=int, default=None,
                    help="Exact single episode number")
parser.add_argument("-r", "--range", type=str, default=None,
                    help="Episode number range(s): e.g. 5, 10-15, 1-5,8,12-14")
parser.add_argument("-t", "--top", type=int, default=10,
                    help="Number of newest episodes when nothing else specified (default: 10)")
args = parser.parse_args()

rss_url = args.rss_url
search_title = args.episode
single_number = args.number
range_str = args.range
top_count = max(1, min(args.top, 100))

print(f"📡 Fetching RSS feed: {rss_url}")
feed = feedparser.parse(rss_url)

if not feed.entries:
    print("❌ No episodes found in the feed.")
    sys.exit(1)

podcast_title = sanitize_filename(feed.feed.get("title", "Podcast"))
download_dir = os.path.join(os.getcwd(), podcast_title)
os.makedirs(download_dir, exist_ok=True)
print(f"📁 Saving to: {download_dir}")

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

# Parse range string into set of target numbers
target_numbers = set()
if range_str:
    parts = [p.strip() for p in range_str.split(',')]
    for part in parts:
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if start > end:
                    start, end = end, start
                target_numbers.update(range(start, end + 1))
            except:
                print(f"⚠️ Invalid range part: {part} (skipping)")
        else:
            try:
                target_numbers.add(int(part))
            except:
                print(f"⚠️ Invalid number: {part} (skipping)")

# Select episodes
episodes = []
seen_numbers = set()

if single_number is not None:
    # Single -n takes highest priority
    for entry in feed.entries:
        if get_episode_number(entry) == single_number:
            episodes.append(entry)
            break
    if not episodes:
        print(f"❌ No episode found with number {single_number}")
        sys.exit(1)
    print(f"🎯 Single episode #{single_number}: {episodes[0].get('title', 'Untitled')}")

elif target_numbers:
    # Range mode
    found_count = 0
    for entry in feed.entries:
        ep_num = get_episode_number(entry)
        if ep_num in target_numbers and ep_num not in seen_numbers:
            episodes.append(entry)
            seen_numbers.add(ep_num)
            found_count += 1
    if not episodes:
        print(f"❌ None of the requested numbers {sorted(target_numbers)} were found")
        sys.exit(1)
    print(f"🎯 Found {found_count}/{len(target_numbers)} episodes in range")

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
    # Default: top N newest
    episodes = feed.entries[:top_count]
    print(f"📥 Downloading top {len(episodes)} newest episode{'s' if len(episodes) != 1 else ''}")

# Sort episodes by episode number (ascending) if we have numbers
def sort_key(entry):
    num = get_episode_number(entry)
    return (num if num is not None else 999999, entry.get('title', ''))

if target_numbers or single_number is not None:
    episodes.sort(key=sort_key)

# Process episodes
for idx, entry in enumerate(episodes, 1):
    title = entry.get("title", f"Episode {idx}").strip()
    ep_num = get_episode_number(entry)
    ep_num_str = f"{ep_num:03d}" if ep_num is not None else f"unk{idx:03d}"
    episode_name = re.sub(r'^(?:ep(?:isode|\.)?|#)?\s*\d+\s*[-:–]\s*', '', title, flags=re.IGNORECASE)
    episode_name = sanitize_filename(episode_name or "Untitled")
    base_name = f"{ep_num_str}_{episode_name}"

    print(f"🎙️  Processing: {base_name}")

    # Audio download
    audio_url = None
    if entry.get("enclosures"):
        for enc in entry.enclosures:
            href = enc.get("href")
            if not href: continue
            typ = enc.get("type", "").lower()
            if typ.startswith("audio/") or href.lower().endswith((".mp3", ".m4a", ".ogg", ".aac")):
                audio_url = href
                break

    audio_path = os.path.join(download_dir, f"{base_name}.mp3")
    audio_exists = os.path.exists(audio_path)

    if audio_url and not audio_exists:
        print(f"   ⬇️  Downloading audio...")
        try:
            r = requests.get(audio_url, stream=True, timeout=30)
            r.raise_for_status()
            with open(audio_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    f.write(chunk)
            print(f"   ✅ Audio saved")
            audio_exists = True
        except Exception as e:
            print(f"   ❌ Audio failed: {e}")
            continue
    elif audio_exists:
        print(f"   ⏭️  Audio already exists")
    else:
        print(f"   ⚠️  No audio available")
        continue

    # Image download
    image_url = None
    if hasattr(entry, "itunes_image") and entry.itunes_image and "href" in entry.itunes_image:
        image_url = entry.itunes_image["href"]
    elif entry.get("image"):
        image_url = entry.image.get("href") if isinstance(entry.image, dict) else entry.image
    if not image_url and hasattr(feed.feed, "itunes_image") and feed.feed.itunes_image and "href" in feed.feed.itunes_image:
        image_url = feed.feed.itunes_image["href"]
    elif not image_url and feed.feed.get("image"):
        image_url = feed.feed.image.get("href") if isinstance(feed.feed.image, dict) else feed.feed.image.get("url")

    img_path = None
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
                print(f"   ✅ Image saved")
            else:
                print(f"   ⏭️  Image already exists")
        except Exception as e:
            print(f"   ❌ Image failed: {e}")
            img_path = None
    else:
        print(f"   ⚠️  No image found")

    # Embed artwork
    if audio_exists and img_path and os.path.exists(img_path):
        print(f"   🖼️  Embedding cover art...")
        try:
            audio = MP3(audio_path, ID3=ID3)
            try:
                audio.add_tags()
            except:
                pass

            mime = 'image/png' if img_path.lower().endswith('.png') else 'image/jpeg'
            with open(img_path, "rb") as imgf:
                audio.tags.add(APIC(
                    encoding=3,
                    mime=mime,
                    type=3,  # front cover
                    desc='Cover',
                    data=imgf.read()
                ))
            audio.save(v2_version=3)  # force ID3v2.3 for broader compatibility
            print(f"   ✅ Artwork embedded")
        except Exception as e:
            print(f"   ❌ Embed failed: {e}")

print("\n🎉 Done!")
print(f"📂 Folder: {download_dir}")
