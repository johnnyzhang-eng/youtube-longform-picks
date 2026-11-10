"""Build index.html from videos.json.  Usage: python3 build.py"""
import json
from html import escape
from pathlib import Path

HERE = Path(__file__).parent
data = json.loads((HERE / "videos.json").read_text(encoding="utf-8"))


def fmt_len(s):
    h, m, sec = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def len_bucket(s):
    return "short" if s < 20 * 60 else "mid" if s <= 60 * 60 else "long"


def card(v, topic):
    url = f"https://www.youtube.com/watch?v={v['id']}"
    attrs = {
        "data-id": v["id"], "data-topic": topic, "data-len": len_bucket(v["seconds"]),
        "data-title": v["title"], "data-channel": v["channel"], "data-ask": v["ask"],
    }
    attr_str = " ".join(f'{k}="{escape(str(x))}"' for k, x in attrs.items())
    return f"""<article class="card" {attr_str}>
  <a class="thumb" href="{url}" target="_blank" rel="noopener">
    <span class="ph">{escape(v['channel'])}</span>
    <img src="https://i.ytimg.com/vi/{v['id']}/mqdefault.jpg" alt="" loading="lazy" onerror="this.remove()">
    <span class="dur">{fmt_len(v['seconds'])}</span>
    <span class="seen-badge">已看</span>
  </a>
  <div class="body">
    <h3><a href="{url}" target="_blank" rel="noopener">{escape(v['title'])}</a></h3>
    <p class="meta">{escape(v['channel'])} · {v['date'][:7]}</p>
    <p class="why">{escape(v['why'])}</p>
    <p class="ask"><b>带着问题看</b>{escape(v['ask'])}</p>
    <div class="actions js-only">
      <button type="button" class="btn-seen">标记已看</button>
      <button type="button" class="btn-copy">复制小记模板</button>
    </div>
  </div>
</article>"""


by_id = {v["id"]: (v, t["key"]) for t in data["topics"] for v in t["videos"]}
total = len(by_id)
starters = "\n".join(card(*by_id[i]) for i in data["starters"])
chips = "\n".join(
    f'<button type="button" class="chip" data-topic="{t["key"]}">{escape(t["name"])}</button>' for t in data["topics"]
)
sections = "\n".join(
    f"""<section class="topic" data-topic="{t['key']}" id="{t['key']}">
  <h2>{escape(t['name'])} <span class="count">{len(t['videos'])}</span></h2>
  <p class="intro">{escape(t['intro'])}</p>
  <div class="grid">
{chr(10).join(card(v, t['key']) for v in t['videos'])}
  </div>
</section>"""
    for t in data["topics"]
)

page = (HERE / "template.html").read_text(encoding="utf-8")
for k, x in {
    "{{UPDATED}}": data["updated"], "{{TOTAL}}": str(total),
    "{{STARTERS}}": starters, "{{CHIPS}}": chips, "{{SECTIONS}}": sections,
}.items():
    page = page.replace(k, x)
(HERE / "index.html").write_text(page, encoding="utf-8")
print(f"index.html: {total} videos, {len(data['topics'])} topics")
