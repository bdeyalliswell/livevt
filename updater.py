#!/usr/bin/env python3
import json
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

PLAYLIST_URL = "https://iptv-org.github.io/iptv/index.m3u"
OUTPUT_FILE = "channels.json"
MAX_WORKERS = 40  # এক সাথে কতগুলো লিংক টেস্ট হবে (থ্রেড সংখ্যা)
TIMEOUT_SECONDS = 4  # লিংক টেস্ট করার সর্বোচ্চ সময়

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*"
}

def parse_extinf_tags(line):
    """M3U ফাইলের #EXTINF লাইন থেকে মেটাডাটা আলাদা করে।"""
    data = {
        "title": "Unknown Channel",
        "logo": "logo.png",
        "country": "Global",
        "language": "General",
        "category": "General"
    }

    # লোগো বের করা
    tvg_logo = re.search(r'tvg-logo="([^"]*)"', line)
    if tvg_logo and tvg_logo.group(1).strip():
        data["logo"] = tvg_logo.group(1).strip()

    # ক্যাটাগরি / গ্রুপ টাইটেল বের করা
    group_title = re.search(r'group-title="([^"]*)"', line)
    if group_title and group_title.group(1).strip():
        data["category"] = group_title.group(1).strip().capitalize()

    # কান্ট্রি কোড বের করা
    tvg_country = re.search(r'tvg-country="([^"]*)"', line)
    if tvg_country and tvg_country.group(1).strip():
        data["country"] = tvg_country.group(1).strip().upper()

    # ভাষা বের করা
    tvg_language = re.search(r'tvg-language="([^"]*)"', line)
    if tvg_language and tvg_language.group(1).strip():
        data["language"] = tvg_language.group(1).strip().capitalize()

    # চ্যানেলের নাম বের করা (কমা চিহ্নের পরের অংশ)
    name_split = line.split(",")
    if len(name_split) > 1:
        clean_name = name_split[-1].strip()
        if clean_name:
            data["title"] = clean_name

    return data

def is_stream_active(url):
    """M3U8 স্ট্রিম লিঙ্কটি সচল (HTTP 200) কিনা তা পরীক্ষা করে।"""
    # ব্রাউজার সিকিউরিটির জন্য শুধু HTTPS লিংক গ্রহণ করা ভালো
    if not url.startswith("https://"):
        return False

    try:
        # ব্যান্ডউইথ বাঁচাতে শুধু হেড বা প্রথম কয়েক বাইট রিকোয়েস্ট পাঠানো হয়
        response = requests.head(url, headers=HEADERS, timeout=TIMEOUT_SECONDS, allow_redirects=True)
        if response.status_code in [200, 302, 301, 206]:
            return True
        
        # কিছু সার্ভার HEAD মেথড ব্লক করে, তাদের জন্য GET ট্রাই করা হয়
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS, stream=True, allow_redirects=True)
        return response.status_code in [200, 206]
    except Exception:
        return False

def check_channel(channel):
    """একটি একক চ্যানেল ভ্যালিডেশন টাস্ক।"""
    if is_stream_active(channel["url"]):
        return channel
    return None

def main():
    print(f"Downloading IPTV playlist from: {PLAYLIST_URL}")
    try:
        res = requests.get(PLAYLIST_URL, headers=HEADERS, timeout=30)
        res.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch playlist: {e}")
        return

    lines = res.text.splitlines()
    raw_channels = []
    current_meta = None

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            current_meta = parse_extinf_tags(line)
        elif line and not line.startswith("#"):
            if current_meta:
                current_meta["url"] = line
                raw_channels.append(current_meta)
                current_meta = None

    print(f"Found {len(raw_channels)} total channels. Checking active streams with {MAX_WORKERS} threads...")

    active_channels = []
    # দ্রুত চেক করার জন্য মাল্টি-থ্রেডিং ব্যবহার
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_channel, ch): ch for ch in raw_channels}
        for future in as_completed(futures):
            result = future.result()
            if result:
                active_channels.append(result)

    print(f"Check completed! Active channels: {len(active_channels)}")

    # JSON ফরম্যাটে সেভ
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(active_channels, f, ensure_ascii=False, indent=2)

    print(f"Saved working channels to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
