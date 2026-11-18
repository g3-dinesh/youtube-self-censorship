"""STAGE 2 (signal) - Ad presence checker.

Decides whether YouTube has attached ad slots to a video, which is a stronger
monetisation probe than watching for a visual ad. It fetches the public watch
page and reads the `ytInitialPlayerResponse` JSON that YouTube ships in the HTML,
looking at adPlacements / playerAds / playabilityStatus / paidContentOverlay.

ONE-DIRECTIONAL RULE (important): ad_config = 1 (ad slots present) is strong
evidence the video IS monetised. ad_config = 0 is weaker evidence (could be a
regional inventory gap, not a policy block). So we trust "ads present", never
"no ads" as proof of demonetisation.

Input
  video ids as arguments, OR --input CSV with a video_id / id column

Output
  outputs/ad_observations.csv   video_id, ad_config, has_ad_placements,
                                has_player_ads, paid_overlay, playable, status

Example
  python src/04_ad_checker.py dQw4w9WgXcQ
  python src/04_ad_checker.py --input outputs/video_index.csv
"""
import argparse, csv, json, os, socket, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, "outputs")
COOKIES = os.path.join(REPO, "data", "www.youtube.com_cookies.txt")
WATCH = "https://www.youtube.com/watch?v="
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
PR_MARKERS = ("var ytInitialPlayerResponse =", "ytInitialPlayerResponse =",
              'ytInitialPlayerResponse"] =')


def force_ipv4():
    """Avoid slow IPv6-blackhole hangs on some networks."""
    orig = socket.getaddrinfo
    socket.getaddrinfo = lambda *a, **k: [ai for ai in orig(*a, **k) if ai[0] == socket.AF_INET]


def load_cookie_header(path):
    if not path or not os.path.exists(path):
        return ""
    pairs = []
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        p = line.rstrip("\n").split("\t")
        if len(p) >= 7 and "youtube" in p[0]:
            pairs.append(f"{p[5]}={p[6]}")
    return "; ".join(pairs)


def fetch_watch(vid, region, cookie_header, timeout):
    url = WATCH + vid + "&gl=" + region + "&hl=en"
    headers = {"User-Agent": UA, "Accept-Language": f"en-{region},en;q=0.9"}
    if cookie_header:
        headers["Cookie"] = cookie_header
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _brace_match(html, start):
    """Return the balanced {...} JSON object beginning at `start`."""
    depth = 0; in_str = False; esc = False
    for i in range(start, len(html)):
        ch = html[i]
        if in_str:
            if esc: esc = False
            elif ch == "\\": esc = True
            elif ch == '"': in_str = False
            continue
        if ch == '"': in_str = True
        elif ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return html[start:i + 1]
    return None


def extract_player_response(html):
    pos = -1
    for marker in PR_MARKERS:
        pos = html.find(marker)
        if pos >= 0:
            pos = html.find("{", pos + len(marker)); break
    if pos < 0:
        return None
    blob = _brace_match(html, pos)
    try:
        return json.loads(blob) if blob else None
    except Exception:
        return None


def read_ad_flags(pr):
    out = {"ad_config": "", "has_ad_placements": 0, "has_player_ads": 0,
           "paid_overlay": 0, "playable": "", "status": "", "reason": ""}
    if not pr:
        out["status"] = "NO_PLAYER_RESPONSE"; return out
    status = pr.get("playabilityStatus") or {}
    out["status"] = status.get("status", "")
    out["reason"] = (status.get("reason") or "")[:60]
    out["playable"] = 1 if status.get("status") == "OK" else 0
    ad_placements = pr.get("adPlacements") or pr.get("adSlots") or []
    out["has_ad_placements"] = 1 if ad_placements else 0
    out["has_player_ads"] = 1 if pr.get("playerAds") else 0
    out["paid_overlay"] = 1 if json.dumps(pr).find("paidContentOverlay") >= 0 else 0
    if out["has_ad_placements"] or out["has_player_ads"]:
        out["ad_config"] = 1                       # ad slots present -> monetised
    elif out["playable"] == 1:
        out["ad_config"] = 0                       # playable, no ad slots (weak)
    return out


def main():
    ap = argparse.ArgumentParser(description="Stage 2 signal: ad-presence checker.")
    ap.add_argument("video_id", nargs="*")
    ap.add_argument("--input", help="CSV with a video_id/id column")
    ap.add_argument("--out", default=os.path.join(OUT, "ad_observations.csv"))
    ap.add_argument("--region", default="US")
    ap.add_argument("--no-cookies", action="store_true")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--sleep", type=float, default=2.0)
    args = ap.parse_args()
    force_ipv4()

    ids = [v.strip() for v in args.video_id if v.strip()]
    if args.input and os.path.exists(args.input):
        for r in csv.DictReader(open(args.input, encoding="utf-8-sig")):
            v = (r.get("video_id") or r.get("id") or "").strip()
            if v: ids.append(v)
    if not ids:
        sys.exit("no video ids (positional or --input csv)")

    cookie_header = "" if args.no_cookies else load_cookie_header(COOKIES)
    os.makedirs(OUT, exist_ok=True)
    fields = ["video_id", "ad_config", "has_ad_placements", "has_player_ads",
              "paid_overlay", "playable", "status", "reason"]
    n_mon = 0
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader()
        for i, vid in enumerate(ids, 1):
            row = {"video_id": vid}
            try:
                row.update(read_ad_flags(extract_player_response(
                    fetch_watch(vid, args.region, cookie_header, args.timeout))))
            except Exception as e:
                row["reason"] = ("err:" + str(e))[:60]
            w.writerow({k: row.get(k, "") for k in fields}); fh.flush()
            n_mon += int(row.get("ad_config") == 1)
            print(f"[{i}/{len(ids)}] {vid} ad_config={row.get('ad_config')} ({row.get('status')})")
            time.sleep(args.sleep)
    print(f"\n-> {args.out}  ({n_mon} with ad slots configured = proven monetised)")


if __name__ == "__main__":
    main()
