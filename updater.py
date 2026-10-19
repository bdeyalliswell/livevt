#!/usr/bin/env python3
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

PLAYLIST_URL = "https://iptv-org.github.io/iptv/index.m3u"
OUTPUT_FILE = "channels.json"
MAX_WORKERS = 30
TIMEOUT = 5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "*/*"
}

def parse_extinf(line):
    data = {
        "title": "Live TV",
        "logo": "logo.png",
        "country": "Global",
        "language": "General",
        "category": "General"
    }
    
    logo = re.search(r'tvg-logo="([^"]*)"', line)
    if logo and logo.group(1).strip():
        data["logo"] = logo.group(1).strip()
        
    group = re.search(r'group-title="([^"]*)"', line)
    if group and group.group(1).strip():
        data["category"] = group.group(1).strip().capitalize()
        
    country = re.search(r'tvg-country="([^"]*)"', line)
    if country and country.group(1).strip():
        data["country"] = country.group(1).strip().upper()
        
    lang = re.search(r'tvg-language="([^"]*)"', line)
    if lang and lang.group(1).strip():
        data["language"] = lang.group(1).strip().capitalize()
        
    parts = line.split(",")
    if len(parts) > 1 and parts[-1].strip():
        data["title"] = parts[-1].strip()
        
    return data

def verify_m3u8_stream(channel):
    url = channel["url"]
    # ব্রাউজার সিকিউরিটির জন্য কেবল HTTPS লিংক ফিল্টার করা হয়
    if not url.startswith("https://"):
        return None
        
    try:
        # শুধু স্ট্যাটাস কোড নয়, প্রথম ৫১২ বাইট পড়ে প্লেলিস্ট কনটেন্ট ভ্যালিড কিনা নিশ্চিত করা হয়
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
        if res.status_code == 200:
            sample = res.raw.read(512).decode("utf-8", errors="ignore")
            # আসল M3U8 ফাইলে #EXTM3U হেডার থাকে
            if "#EXTM3U" in sample or "#EXT-X-" in sample:
                return channel
    except Exception:
        pass
    return None

def main():
    print("Downloading playlist...")
    try:
        res = requests.get(PLAYLIST_URL, headers=HEADERS, timeout=30)
        res.raise_for_status()
    except Exception as e:
        print(f"Error downloading playlist: {e}")
        return

    raw_items = []
    current = None
    for line in res.text.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF:"):
            current = parse_extinf(line)
        elif line and not line.startswith("#") and current:
            current["url"] = line
            raw_items.append(current)
            current = None

    print(f"Total raw streams found: {len(raw_items)}. Verifying working streams...")
    verified = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(verify_m3u8_stream, ch): ch for ch in raw_items}
        for f in as_completed(futures):
            res_ch = f.result()
            if res_ch:
                verified.append(res_ch)

    print(f"Verified working channels: {len(verified)}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(verified, f, ensure_ascii=False, indent=2)
    print("channels.json successfully generated!")

if __name__ == "__main__":
    main()
