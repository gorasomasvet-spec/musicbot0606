import yt_dlp

def search_music(query):
    ydl_opts = {
        "quiet": True,
        "extract_flat": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(
            f"ytsearch5:{query}",
            download=False
        )

    tracks = []

    for item in result["entries"]:
        tracks.append({
            "title": item["title"],
            "url": f"https://youtube.com/watch?v={item['id']}"
        })

    return tracks