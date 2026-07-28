"""修復 disc/track 數字標籤被 str(list) 污染的歷史資料。

## 背景

早期寫入路徑（FLAC 的 `audio[key.upper()] = [str(value)]`）若收到 list，
會把 Python 的字面表示直接寫進標籤，在檔案裡留下：

    discnumber  = "['1/2']"
    tracknumber = "['6/47']"

這種值會讓 navidrome 之類的播放器解析成 0，曲序全亂。
mp3tag_writer.coerce_number() 已擋住新的污染來源，本腳本負責清理既有檔案。

## 偵測方式

直接開檔掃描全庫在雲端掛載（rclone）上極慢——實測 1457 個檔案會卡在 I/O 數小時，
因為 vfs-cache-mode=full 每開一個檔就要下載整份。

因此改用零檔案讀取的交叉比對：
  - nextags 的 Redis 快取值（已由加固後的 reader 正規化）
  - navidrome 對同一檔案的解析結果
兩邊不一致（nextags 有值、navidrome 得到 0）就代表檔案裡是畸形值。

先在 host 上匯出 navidrome 的解析結果：

    sqlite3 -json "file:/opt/music-stack/navidrome/data/navidrome.db?mode=ro" \
      "SELECT l.name AS lib, m.path, m.track_number, m.disc_number
         FROM media_file m JOIN library l ON l.id = m.library_id;" > /tmp/nd.json
    docker cp /tmp/nd.json nextags-backend-1:/tmp/nd.json

## 用法（在 backend 容器內）

    # 偵測，輸出待修清單
    python scripts/fix_number_tags.py --detect --navidrome-json /tmp/nd.json \
        --paths-file /tmp/suspects.json

    # 預演（預設不寫入）
    python scripts/fix_number_tags.py --paths-file /tmp/suspects.json

    # 實際寫入
    python scripts/fix_number_tags.py --paths-file /tmp/suspects.json --apply

## 寫入格式

值取自 Redis 快取，寫入交給 write_tags()，由它產生各容器的原生格式：
  FLAC / OGG -> TRACKNUMBER=6 + TRACKTOTAL=47（Vorbis 慣例：分成兩欄）
  MP3        -> TRCK="6/47"（ID3v2 規範格式，斜線在這裡才是對的）
  MP4        -> trkn=(6, 47)

寫入前會把原始標籤存進 backup JSON，可回溯。
"""
import argparse
import json
import os

import mutagen

from app.dependencies.mp3tag_writer import write_tags
from app.dependencies.redis_cache import redis_cache
from app.router.config import get_config

MUSIC_ROOT = "/Music"
NUMBER_FIELDS = ("tracknumber", "tracktotal", "discnumber", "disctotal")
RAW_KEYS_OF_INTEREST = (
    "tracknumber", "tracktotal", "totaltracks",
    "discnumber", "disctotal", "totaldiscs",
    "TRCK", "TPOS", "trkn", "disk",
)


def _to_int(value) -> int:
    if isinstance(value, list):
        value = value[0] if value else ""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def cached_tags(path: str) -> dict:
    blob = redis_cache.client.get(redis_cache._get_cache_key(path))
    return json.loads(blob).get("tags", {}) if blob else {}


def raw_number_tags(path: str):
    """只取 disc/track 相關的原始標籤，供備份與前後比對。"""
    audio = mutagen.File(path)
    if audio is None or not audio.tags:
        return None
    out = {}
    for key, value in audio.tags.items():
        if str(key).lower() in RAW_KEYS_OF_INTEREST or str(key) in RAW_KEYS_OF_INTEREST:
            out[str(key)] = [str(v) for v in value] if isinstance(value, list) else str(value)
    return out


def detect(navidrome_json: str) -> list:
    """比對 nextags 快取與 navidrome 解析結果，找出檔案內仍是畸形值的路徑。"""
    with open(navidrome_json, encoding="utf-8") as handle:
        nd = {(row["lib"], row["path"]): row for row in json.load(handle)}

    suspects, unmatched = [], 0
    for path in sorted(redis_cache.client.smembers("audio_catalog:paths")):
        library, _, relative = path[len(MUSIC_ROOT) + 1:].partition("/")
        row = nd.get((library, relative))
        if row is None:
            unmatched += 1
            continue

        tags = cached_tags(path)
        if not tags:
            continue

        # nextags 讀得出數字、navidrome 卻是 0 -> navidrome 解析失敗 -> 檔案內是畸形值
        if (_to_int(tags.get("tracknumber")) > 0 and row["track_number"] == 0) or \
           (_to_int(tags.get("discnumber")) > 0 and row["disc_number"] == 0):
            suspects.append(path)

    if unmatched:
        print(f"警告：{unmatched} 個路徑在 navidrome 中找不到對應，已略過", flush=True)
    return suspects


def desired_tags(path: str) -> dict:
    """從快取取出已正規化的純數字值。"""
    tags = cached_tags(path)
    result = {}
    for field in NUMBER_FIELDS:
        value = tags.get(field)
        if isinstance(value, list):
            value = value[0] if value else ""
        text = str(value).strip() if value else ""
        if text.isdigit():
            result[field] = text
    return result


def repair(paths: list, backup_file: str, apply: bool) -> None:
    folder_paths = {name: os.path.join(MUSIC_ROOT, name) for name in (get_config("allow_folders") or [])}

    backup = {}
    if os.path.exists(backup_file):
        with open(backup_file, encoding="utf-8") as handle:
            backup = json.load(handle)

    fixed = failed = skipped = 0
    for index, path in enumerate(paths, start=1):
        label = path.split("/Music/")[-1]
        if not os.path.exists(path):
            print(f"[{index}/{len(paths)}] MISS {label}", flush=True)
            skipped += 1
            continue

        before = raw_number_tags(path)
        desired = desired_tags(path)
        if not desired:
            print(f"[{index}/{len(paths)}] SKIP 無可用正規化值 {label}", flush=True)
            skipped += 1
            continue

        print(f"[{index}/{len(paths)}] {label}", flush=True)
        print(f"    before: {before}", flush=True)
        print(f"    write : {desired}", flush=True)

        if not apply:
            continue

        backup.setdefault(path, before)
        if write_tags(path, dict(desired)):
            redis_cache.upsert_audio_record(path, folder_paths=folder_paths)
            print(f"    after : {raw_number_tags(path)}", flush=True)
            fixed += 1
        else:
            print("    FAILED", flush=True)
            failed += 1

        # 逐檔寫回備份，中途中斷也不會遺失
        with open(backup_file, "w", encoding="utf-8") as handle:
            json.dump(backup, handle, ensure_ascii=False, indent=1)

    mode = "APPLIED" if apply else "DRY RUN"
    print(f"\n=== {mode} === 修復 {fixed} / 失敗 {failed} / 跳過 {skipped} / 共 {len(paths)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--detect", action="store_true", help="偵測待修檔案並寫入 --paths-file 後結束")
    parser.add_argument("--navidrome-json", help="navidrome media_file 匯出的 JSON（--detect 時必填）")
    parser.add_argument("--paths-file", default="/tmp/suspects.json", help="待修路徑清單 JSON")
    parser.add_argument("--backup", default="/app/data/tagfix_backup.json", help="原始標籤備份位置")
    parser.add_argument("--apply", action="store_true", help="實際寫入；預設只做預演")
    args = parser.parse_args()

    if args.detect:
        if not args.navidrome_json:
            parser.error("--detect 需要搭配 --navidrome-json")
        suspects = detect(args.navidrome_json)
        with open(args.paths_file, "w", encoding="utf-8") as handle:
            json.dump(suspects, handle, ensure_ascii=False, indent=1)
        print(f"偵測到 {len(suspects)} 個待修檔案，清單已寫入 {args.paths_file}")
        return

    with open(args.paths_file, encoding="utf-8") as handle:
        paths = json.load(handle)
    repair(paths, args.backup, args.apply)


if __name__ == "__main__":
    main()
