import os
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

BASE_URL = "https://ai-rail-freight-opti-d8ma.example"
START_PATHS = ["/", "/routes", "/forecast", "/tariffs", "/map", "/about"]
OUTPUT_ROOT = os.path.abspath(os.path.dirname(__file__))

seen = set()
queue = list(START_PATHS)

internal_paths = set()
internal_paths.update(START_PATHS)

link_re = re.compile(r'href=["\'](/[^"\']*)')
img_re = re.compile(r'src=["\'](https?://[^"\']+|/[^"\']*)')
asset_re = re.compile(r'(?:src|href)=["\'](/assets/[^"\']*)')

os.makedirs(OUTPUT_ROOT, exist_ok=True)

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch_url(path):
    url = urljoin(BASE_URL, path)
    print(f"Fetching {url}")
    req = Request(url, headers=headers)
    with urlopen(req, timeout=30) as resp:
        content_type = resp.headers.get("Content-Type", "")
        body = resp.read()
        if "charset=" in content_type:
            body = body.decode(content_type.split("charset=")[-1].split(";")[0].strip(), errors="replace")
        else:
            body = body.decode("utf-8", errors="replace")
    return body


def normalize_path(path):
    if path.startswith(BASE_URL):
        path = urlparse(path).path
    if path.startswith("//"):
        return None
    parsed = urlparse(path)
    if parsed.scheme and parsed.scheme not in ["http", "https"]:
        return None
    if parsed.scheme in ["http", "https"]:
        if urlparse(path).netloc != urlparse(BASE_URL).netloc:
            return None
        path = urlparse(path).path
    if not path.startswith("/"):
        return None
    if path.endswith("/"):
        return path
    ext = os.path.splitext(parsed.path)[1].lower()
    if ext and ext not in {".html", ""}:
        return None
    return path


def save_html(path, html):
    if path == "/":
        out_path = os.path.join(OUTPUT_ROOT, "index.html")
    else:
        clean = path.strip("/")
        dir_path = os.path.join(OUTPUT_ROOT, clean)
        os.makedirs(dir_path, exist_ok=True)
        out_path = os.path.join(dir_path, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved {out_path}")


def rewrite_asset_paths(html):
    # preserve root-relative asset paths for local server.
    html = re.sub(r'href=["\"]/assets/', 'href="/assets/', html)
    html = re.sub(r'src=["\"]/assets/', 'src="/assets/', html)
    return html


while queue:
    path = queue.pop(0)
    if path in seen:
        continue
    seen.add(path)

    try:
        html = fetch_url(path)
    except Exception as exc:
        print(f"Failed to fetch {path}: {exc}")
        continue

    html = rewrite_asset_paths(html)
    save_html(path, html)

    for match in link_re.findall(html):
        normalized = normalize_path(match.split("#")[0])
        if normalized and normalized not in seen and normalized not in internal_paths:
            internal_paths.add(normalized)
            queue.append(normalized)

    for img in img_re.findall(html):
        normalized = normalize_path(img.split("#")[0])
        if normalized and normalized not in internal_paths:
            internal_paths.add(normalized)
            queue.append(normalized)

print("Done. Pages fetched:")
for p in sorted(seen):
    print(p)
