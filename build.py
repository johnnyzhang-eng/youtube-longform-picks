"""Build index.html from videos.json.  Usage: python3 build.py"""
import json
from html import escape
from pathlib import Path

HERE = Path(__file__).parent
data = json.loads((HERE / "videos.json").read_text(encoding="utf-8"))


def fmt_len(s):
    h, m, sec = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def fmt_hm(s):
    h, m = s // 3600, s % 3600 // 60
    return (f"{h} 小时 " if h else "") + f"{m} 分"


def fmt_tc(s):
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def len_bucket(s):
    return "short" if s < 20 * 60 else "mid" if s <= 60 * 60 else "long"


def card(v, step):
    url = f"https://www.youtube.com/watch?v={v['id']}"
    step_html = f'<div class="step" aria-label="第 {step} 步"><span>{step:02d}</span></div>' if step else ""
    points = ""
    if v.get("points"):
        items = "".join(f"<li>{escape(p)}</li>" for p in v["points"])
        points = f'<details class="points nojs-only"><summary>参考要点</summary><ul>{items}</ul></details>'
    return f"""<article class="v" id="v-{v['id']}" data-id="{v['id']}">
  {step_html}
  <a class="thumb" href="{url}" target="_blank" rel="noopener" data-open>
    <span class="ph">{escape(v['channel'])}</span>
    <img src="https://i.ytimg.com/vi/{v['id']}/mqdefault.jpg" alt="" loading="lazy" onerror="this.remove()">
    <span class="play js-only" aria-hidden="true">▶ 看和记</span>
    <span class="dur">{fmt_len(v['seconds'])}</span>
    <span class="seen-badge">已看</span>
  </a>
  <div class="body">
    <h4><a href="{url}" target="_blank" rel="noopener">{escape(v['title'])}</a></h4>
    <p class="meta">{escape(v['channel'])} · {v['date'][:7]}<span class="note-flag">有小记</span></p>
    <p class="why">{escape(v['why'])}</p>
    <p class="ask"><b aria-label="带着问题看" title="带着问题看">问</b><span>{escape(v['ask'])}</span></p>
    {points}
    <div class="actions js-only">
      <button type="button" class="btn primary" data-open>看和记</button>
      <button type="button" class="btn" data-seen aria-pressed="false">标记已看</button>
    </div>
  </div>
</article>"""


zones_html, toc_html, js_data, scrub_html = [], [], [], []
for z in data["zones"]:
    segs, z_secs = [], sum(v["seconds"] for t in z["topics"] for v in t["videos"])
    toc_html.append(f'<a class="toc-zone" href="#z-{z["key"]}">{escape(z["name"])}</a>')
    topics_html = []
    for t in z["topics"]:
        cards = []
        for i, v in enumerate(t["videos"], 1):
            step = i if t.get("ordered") else 0
            cards.append(card(v, step))
            js_data.append({
                **{k: v[k] for k in ("id", "title", "channel", "seconds", "date", "why", "ask")},
                "points": v.get("points", []), "len": len_bucket(v["seconds"]), "step": step,
                "zone": z["key"], "zoneName": z["name"], "topic": t["key"], "topicName": t["name"],
            })
        n = len(t["videos"])
        secs = sum(v["seconds"] for v in t["videos"])
        segs.append(
            f'<a class="seg" href="#t-{t["key"]}" data-topic="{t["key"]}" style="flex-grow:{secs}" '
            f'title="{escape(t["name"])} · {fmt_hm(secs)}"><i></i><span class="sr">{escape(t["name"])}，{fmt_hm(secs)}</span></a>'
        )
        toc_html.append(
            f'<a class="toc-topic" href="#t-{t["key"]}" data-topic="{t["key"]}">'
            f'<span>{escape(t["name"])}</span><span class="n">{n}</span></a>'
        )
        topics_html.append(f"""<section class="topic" id="t-{t['key']}" data-topic="{t['key']}">
  <header class="topic-head">
    <h3>{escape(t['name'])}</h3>
    <span class="prog"><span class="bar js-only"><i></i></span><span class="num">{n} 个</span><span class="rt">{fmt_hm(secs)}</span></span>
  </header>
  <p class="intro">{escape(t['intro'])}</p>
  <div class="list">
{chr(10).join(cards)}
  </div>
</section>""")
    scrub_html.append(
        f'<div class="sz sz-{z["key"]}" style="flex-grow:{z_secs}"><div class="segs">{"".join(segs)}</div>'
        f'<a class="zl" href="#z-{z["key"]}"><b>{escape(z["name"])}</b><span>{fmt_hm(z_secs)}</span></a></div>'
    )
    tag = "按顺序 · 看完自测" if z["key"] == "learn" else "不分先后"
    zones_html.append(f"""<section class="zone zone-{z['key']}" id="z-{z['key']}" data-zone="{z['key']}">
  <header class="zone-head">
    <h2>{escape(z['name'])}</h2><span class="tag">{tag}</span>
    <p>{escape(z['intro'])}</p>
  </header>
{chr(10).join(topics_html)}
</section>""")

page = (HERE / "template.html").read_text(encoding="utf-8")
for k, x in {
    "{{UPDATED}}": data["updated"], "{{TOTAL}}": str(len(js_data)),
    "{{SCRUB}}": "\n".join(scrub_html), "{{RUNTIME}}": fmt_tc(sum(v["seconds"] for v in js_data)),
    "{{TOC}}": "\n".join(toc_html), "{{ZONES}}": "\n".join(zones_html),
    "{{DATA}}": json.dumps(js_data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"),
}.items():
    page = page.replace(k, x)
(HERE / "index.html").write_text(page, encoding="utf-8")
print(f"index.html: {len(js_data)} videos, {sum(len(z['topics']) for z in data['zones'])} topics")
