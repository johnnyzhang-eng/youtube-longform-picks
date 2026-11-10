"""Score one round of candidates and sync the result into videos.json.

Usage: python3 tools/score.py pool/round-01.json
Every number used here lives in the round file's "config", so the page can show the same rules.
"""
import json, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GROUPS = [("p-ai", "AI：新方法和原理"), ("p-now", "AI：现在的人在想什么"), ("p-math", "数学与科普"), ("p-data", "数据工程"), ("p-people", "人物、历史与认知")]
ASK = "看完用自己的话说：它最核心的一个观点或结论是什么？"


def score(c, cfg, today):
    """Return (parts, reject_reason). parts = [source, endorse, topic, fresh]."""
    if c["seconds"] < cfg["min_seconds"]: return None, "不到 15 分钟"
    if c["seconds"] > cfg["max_seconds"]: return None, "超过 2 小时 30 分"
    if c["topic"] == 0: return None, "和主题无关"
    tier = next((t for t, names in cfg["tiers"].items() if c["channel"] in names), "none") if c["whitelist"] else "none"
    source = cfg["source"][tier]
    endorse = next((pts for floor, pts in cfg["endorse"] if c["hn"] >= floor), 0)
    topic = cfg["topic"][str(c["topic"])]
    if c["kind"] == "d":
        fresh = cfg["fresh"]["durable"]
    else:
        age = (today - date.fromisoformat(c["date"])).days
        fresh = next((pts for days, pts in cfg["fresh"]["status"] if age <= days), None)
        if fresh is None: return None, "谈现状的内容超过 180 天"
    return [source, endorse, topic, fresh], ""


def main(path):
    rd = json.loads(Path(path).read_text(encoding="utf-8")); cfg = rd["config"]; today = date.fromisoformat(rd["date"])
    for c in rd["candidates"]:
        c["parts"], c["reason"] = score(c, cfg, today)
        c["score"] = sum(c["parts"]) if c["parts"] else 0
        c["picked"] = False
    ranked = [c for c in rd["candidates"] if c["parts"]]
    ranked.sort(key=lambda c: c["date"], reverse=True)       # newest first ...
    ranked.sort(key=lambda c: (-c["score"], -c["hn"]))       # ... within the same score and endorsement (sort is stable)
    per, n = {}, 0
    for c in ranked:
        if c["score"] < cfg["threshold"]: c["reason"] = f"低于 {cfg['threshold']} 分"
        elif per.get(c["channel"], 0) >= cfg["per_channel"]: c["reason"] = f"这个频道已经有 {cfg['per_channel']} 个"
        elif n >= cfg["pool_cap"]: c["reason"] = "候选池满了"
        else: c["picked"] = True; per[c["channel"]] = per.get(c["channel"], 0) + 1; n += 1
    Path(path).write_text(json.dumps(rd, ensure_ascii=False, indent=1), encoding="utf-8")

    vp = ROOT / "videos.json"; d = json.loads(vp.read_text(encoding="utf-8"))
    names = ["来源", "推荐", "主题", "时效"]
    topics = []
    for key, name in GROUPS:
        vids = [{"id": c["id"], "title": c["title"], "channel": c["channel"], "seconds": c["seconds"], "date": c["date"], "why": c["note"], "ask": ASK,
                 "score": c["score"], "parts": c["parts"], **({"noembed": True} if not c["embed"] else {})}
                for c in ranked if c["picked"] and c["group"] == key]
        if vids: topics.append({"key": key, "kind": "pool", "ordered": False, "name": name, "intro": "", "videos": vids})
    assert sum(len(t["videos"]) for t in topics) == n, "a picked video has no group or note"
    pool = next(z for z in d["zones"] if z["key"] == "pool")
    pool["topics"] = topics
    pool["round"] = {"file": str(Path(path).name), "n": rd["round"], "date": rd["date"], "raw": rd["collected"], "long": len(rd["candidates"]), "picked": n}
    pool["intro"] = f"第 {rd['round']} 期，{rd['date']} 按下面“我们怎么选片”的算法算出来的，每个视频都标了得分。没有逐个看过，介绍来自标题和简介。想看哪个直接看，池子定期换新。"
    vp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"scored {len(ranked)} | picked {n} | rejected before scoring {len(rd['candidates']) - len(ranked)}")
    for c in ranked: print(f'{"+" if c["picked"] else " "} {c["score"]:>3} {c["parts"]} {c["channel"][:20]:<20} {c["title"][:44]:<44} {c["reason"]}')


if __name__ == "__main__":
    main(sys.argv[1])
