import os, json, shutil
from datetime import datetime, timezone

def _ext(p: str) -> str:
    e = os.path.splitext(os.path.basename(p or ""))[1]
    return e if e else ".bin"

def publish_dashboard(html: str, inline_images: dict | None, attachments: list | None, settings: dict, equity: float, cash: float, daily_pnl: float, total_pl: float, as_of_iso: str) -> str:
    site = settings.get("site", {})
    if not site or not site.get("enabled"):
        return ""
    out_dir = site.get("public_dir", "")
    if not out_dir:
        return ""
    os.makedirs(out_dir, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    if inline_images:
        for cid, path in inline_images.items():
            if path and os.path.exists(path):
                shutil.copy2(path, os.path.join(out_dir, f"{cid}_{ts}{_ext(path)}"))

    if attachments:
        for path in attachments:
            if path and os.path.exists(path):
                base = os.path.splitext(os.path.basename(path))[0]
                shutil.copy2(path, os.path.join(out_dir, f"{base}_{ts}{_ext(path)}"))

    meta = {
        "equity": float(equity),
        "cash": float(cash),
        "daily_pnl": float(daily_pnl),
        "total_pl": float(total_pl),
        "as_of": as_of_iso or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)

    if site.get("write_index"):
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(html)

    return os.path.join(out_dir, "meta.json")
