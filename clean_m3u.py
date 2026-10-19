import concurrent.futures
import requests

# মূল রিপোজিটরির লাইভ Raw লিংক
SOURCE_URL = (
    "https://raw.githubusercontent.com/fisherbryant/iptv_English/main/all.m3u"
)
OUTPUT_FILE = "active_playlist.m3u"
TIMEOUT = 5
MAX_WORKERS = 25

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def check_stream(item):
    extinf, url = item
    try:
        response = requests.get(
            url, headers=HEADERS, timeout=TIMEOUT, stream=True
        )
        if response.status_code == 200:
            print(f"[ACTIVE] {url}")
            return item
    except Exception:
        pass
    print(f"[DEAD] {url}")
    return None


def main():
    print("Fetching fresh playlist from source repository...")
    try:
        res = requests.get(SOURCE_URL, headers=HEADERS, timeout=15)
        lines = [line.strip() for line in res.text.splitlines() if line.strip()]
    except Exception as e:
        print(f"Error fetching source: {e}")
        return

    header = lines[0] if lines[0].startswith("#EXTM3U") else "#EXTM3U"
    channels = []

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF"):
            if i + 1 < len(lines) and not lines[i + 1].startswith("#"):
                channels.append((line, lines[i + 1]))
                i += 2
                continue
        i += 1

    print(f"Total Channels Checked: {len(channels)}")

    active_channels = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:
        results = executor.map(check_stream, channels)
        for r in results:
            if r:
                active_channels.append(r)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"{header}\n\n")
        for extinf, url in active_channels:
            f.write(f"{extinf}\n{url}\n\n")

    print(
        f"Completed! Active: {len(active_channels)} saved to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
