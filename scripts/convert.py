#!/usr/bin/env python3
"""Anime character -> realistic photo via OpenLux.

Pipeline: image2.5 edit of the original -> final PNG + comparison reel. Optional
(--depth): a Seedream depth map from a prompt is passed as a second reference.
Stdlib + Pillow only.

usage:
  python convert.py --input char.png --body body.txt --out outputs/job
  python convert.py --input char.png --body body.txt --depth --depth-prompt depth.txt --out outputs/job
  python convert.py --input chibi.png --prep-prompt prep.txt --out outputs/job
"""
import argparse, base64, json, math, mimetypes, os, sys, time, uuid, urllib.request, urllib.error
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_reel import build as build_reel

BASE = "https://api.openlux.ai/v1"
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAD_DEPTH = os.path.join(SKILL_DIR, "templates", "head_depth.txt")


def find_key():
    key = os.environ.get("OPENLUX_API_KEY")
    if not key:
        path = os.path.join(SKILL_DIR, "openlux_key.txt")
        if os.path.isfile(path):
            key = open(path, encoding="utf-8").read().strip()
    return key or None


def api_key():
    key = find_key()
    if not key:
        sys.exit("No API key: set OPENLUX_API_KEY or put the key in openlux_key.txt next to SKILL.md")
    return key


def request(url, body, ctype, retries=2):
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Authorization": f"Bearer {api_key()}", "Content-Type": ctype})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:1500]
            if e.code < 500 or attempt == retries:
                raise RuntimeError(f"HTTP {e.code}: {msg}")
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
            if attempt == retries:
                raise RuntimeError(f"Network error after {retries + 1} tries: {e}")
        print(f"retrying ({attempt + 1}/{retries})...", file=sys.stderr)
        time.sleep(5 * (attempt + 1))


def save_first(d, path):
    for item in d.get("data", []):
        if item.get("b64_json"):
            open(path, "wb").write(base64.b64decode(item["b64_json"]))
            return path
        if item.get("url"):
            urllib.request.urlretrieve(item["url"], path)
            return path
    raise RuntimeError("No image returned: " + json.dumps(d, ensure_ascii=False)[:1500])


def edit_size(w, h):
    # image2.5 only offers 1:1, 2:3 and 3:2
    r = w / h
    if r >= 1.25:
        return "1536x1024"
    if r <= 0.8:
        return "1024x1536"
    return "1024x1024"


def depth_size(w, h):
    # keep the input aspect exactly at ~4 MP so the depth map lines up with the original
    r = w / h
    dw = round(math.sqrt(2048 * 2048 * r) / 16) * 16
    dh = round(dw / r / 16) * 16
    return f"{dw}x{dh}"


def make_depth(src, prompt, out_path, model):
    w, h = Image.open(src).size
    mt = mimetypes.guess_type(src)[0] or "image/jpeg"
    body = {"model": model, "prompt": prompt, "size": depth_size(w, h),
            "response_format": "b64_json", "watermark": False,
            "image": f"data:{mt};base64," + base64.b64encode(open(src, "rb").read()).decode()}
    d = request(f"{BASE}/images/generations", json.dumps(body).encode(), "application/json")
    return save_first(d, out_path)


def multipart(fields, files):
    b = uuid.uuid4().hex
    out = bytearray()
    for k, v in fields.items():
        out += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    for k, path in files:
        mt = mimetypes.guess_type(path)[0] or "application/octet-stream"
        out += (f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"; "
                f"filename=\"{os.path.basename(path)}\"\r\nContent-Type: {mt}\r\n\r\n").encode()
        out += open(path, "rb").read() + b"\r\n"
    out += f"--{b}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={b}"


def make_final(images, prompt, size, out_path, model, quality):
    fields = {"model": model, "prompt": prompt, "size": size, "n": 1, "quality": quality}
    key = "image" if len(images) == 1 else "image[]"
    body, ct = multipart(fields, [(key, p) for p in images])
    try:
        d = request(f"{BASE}/images/edits", body, ct)
    except RuntimeError as e:
        # the -c group is a separate quota/route for the same model
        print(f"{model} failed ({e}); trying {model}-c", file=sys.stderr)
        fields["model"] = model + "-c"
        body, ct = multipart(fields, [(key, p) for p in images])
        d = request(f"{BASE}/images/edits", body, ct)
    return save_first(d, out_path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", help="only report whether an API key is configured")
    p.add_argument("--input")
    p.add_argument("--body", help="filled prompt body (from templates/body_real.md)")
    p.add_argument("--prep-prompt", help="step 0: redraw --input as a close-up anime image with this prompt, then stop")
    p.add_argument("--original", help="after step 0: the untouched original, shown first in the reel")
    p.add_argument("--size", help="output size override; default 1024x1024 for --prep-prompt, else closest to input")
    p.add_argument("--depth-prompt", help="filled depth prompt (from templates/depth.md)")
    p.add_argument("--depth", action="store_true", help="also build a prompt-based depth map (off by default)")
    p.add_argument("--out", default="outputs")
    p.add_argument("--name", default=None)
    p.add_argument("--model", default="gpt-image-2.5-sunburst")
    p.add_argument("--quality", default="high")
    p.add_argument("--depth-model", default="doubao-seedream-5-0-pro-260628")
    a = p.parse_args()

    if a.check:
        print("api: ready" if find_key() else "api: no key")
        sys.exit(0 if find_key() else 1)
    if not a.input or not (a.body or a.prep_prompt):
        sys.exit("--input plus --body (or --prep-prompt) are required")

    use_depth = a.depth and not a.prep_prompt
    if use_depth and not a.depth_prompt:
        sys.exit("--depth needs --depth-prompt")

    os.makedirs(a.out, exist_ok=True)
    name = a.name or os.path.splitext(os.path.basename(a.input))[0]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    t = time.time()

    src = os.path.join(a.out, f"{name}-input-{stamp}.jpg")
    im = Image.open(a.input).convert("RGB")
    im.save(src, quality=95)

    if a.prep_prompt:
        prompt = open(a.prep_prompt, encoding="utf-8").read().strip()
        try:
            prep = make_final([src], prompt, a.size or "1024x1024",
                              os.path.join(a.out, f"{name}-prep-{stamp}.png"), a.model, a.quality)
        except RuntimeError as e:
            sys.exit(str(e))
        print(json.dumps({"input": src, "prep": prep, "seconds": round(time.time() - t, 1)}, ensure_ascii=False))
        return

    body = open(a.body, encoding="utf-8").read().strip()
    result = {"input": src, "size": a.size or edit_size(*im.size), "depth": None}
    try:
        images = [src]
        if use_depth:
            depth_prompt = open(a.depth_prompt, encoding="utf-8").read().strip()
            depth = make_depth(src, depth_prompt, os.path.join(a.out, f"{name}-depth-{stamp}.jpg"), a.depth_model)
            images.append(depth)
            result["depth"] = depth
            body = open(HEAD_DEPTH, encoding="utf-8").read().strip() + "\n\n" + body
        result["final"] = make_final(images, body, result["size"],
                                     os.path.join(a.out, f"{name}-{stamp}.png"), a.model, a.quality)
    except RuntimeError as e:
        sys.exit(str(e))
    panels = [("原图", a.original), ("漫画特写", src)] if a.original else [("原图", src)]
    result["reel"] = build_reel(os.path.join(a.out, f"{name}-compare-{stamp}.jpg"),
                                panels + [("成片", result["final"])])
    result["seconds"] = round(time.time() - t, 1)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
