"""Build index.html from videos.json.  Usage: python3 build.py"""
import json
from html import escape
from pathlib import Path

HERE = Path(__file__).parent
data = json.loads((HERE / "videos.json").read_text(encoding="utf-8"))
BY_ID = {v["id"]: v for z in data["zones"] for t in z["topics"] for v in t["videos"]}


def fmt_len(s):
    h, m, sec = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def len_bucket(s):
    return "short" if s < 20 * 60 else "mid" if s <= 60 * 60 else "long"


def short_title(v):
    return v["title"].split(" | ")[0]


def card(v, step):
    url = f"https://www.youtube.com/watch?v={v['id']}"
    step_html = f'<div class="step" aria-label="第 {step} 步"><span>{step:02d}</span></div>' if step else ""
    points = supply = ""
    if v.get("points"):
        items = "".join(f"<li>{escape(p)}</li>" for p in v["points"])
        label = f"参考要点（已对照{v['checked']}）" if v.get("checked") else "参考要点（未核对）"
        points = f'<details class="points nojs-only"><summary>{label}</summary><ul>{items}</ul></details>'
    if v.get("supply"):
        links = "、".join(
            f'<a href="#v-{i}" data-goto="{i}">{escape(short_title(BY_ID[i]))}</a>' for i in v["supply"]
        )
        supply = f'<p class="supply">卡在计算上？先补：{links}</p>'
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
    <p class="meta">{escape(v['channel'])} · {v['date'][:7]}<span class="note-flag">有小记</span><span class="due-flag">该复述了</span></p>
    <p class="why">{escape(v['why'])}</p>
    <p class="ask"><b aria-label="带着问题看" title="带着问题看">问</b><span>{escape(v['ask'])}</span></p>
    {supply}
    {points}
    <div class="actions js-only">
      <button type="button" class="btn primary" data-open>看和记</button>
      <button type="button" class="btn" data-seen aria-pressed="false">标记已看</button>
    </div>
  </div>
</article>"""


zones_html, toc_html, js_data, steps_html, main_html = [], [], [], [], ""
for z in data["zones"]:
    toc_html.append(f'<a class="toc-zone" href="#z-{z["key"]}">{escape(z["name"])}</a>')
    topics_html, seen_branch = [], False
    for t in z["topics"]:
        kind, cards = t["kind"], []
        for i, v in enumerate(t["videos"], 1):
            step = i if t.get("ordered") else 0
            cards.append(card(v, step))
            js_data.append({
                **{k: v[k] for k in ("id", "title", "channel", "seconds", "date", "why", "ask")},
                "points": v.get("points", []), "checked": v.get("checked", ""), "src": v.get("src", ""), "noembed": bool(v.get("noembed")),
                "len": len_bucket(v["seconds"]), "step": step, "kind": kind,
                "zone": z["key"], "zoneName": z["name"], "topic": t["key"], "topicName": t["name"],
            })
            if kind == "main":
                steps_html.append(
                    f'<li><a class="st" href="#v-{v["id"]}" data-step="{v["id"]}"><b>{i:02d}</b>'
                    f'<span class="st-name">{escape(v["short"])}</span><span class="st-state">没看</span></a></li>'
                )
        n = len(t["videos"])
        if kind == "branch" and not seen_branch:
            toc_html.append('<span class="toc-sub">分支，按需打开</span>')
            seen_branch = True
        toc_html.append(
            f'<a class="toc-topic" href="#t-{t["key"]}" data-topic="{t["key"]}">'
            f'<span>{escape(t["name"])}</span><span class="n">{n}</span></a>'
        )
        bar = '<span class="bar js-only"><i></i></span>' if kind in ("main", "branch") else ""
        head = f'<h3>{escape(t["name"])}</h3><span class="prog">{bar}<span class="num">{n} 个</span></span>'
        link = ""
        if t.get("link"):
            link = f'<p class="intro"><a class="ext" href="{t["link"]["url"]}" target="_blank" rel="noopener">{escape(t["link"]["text"])} ↗</a></p>'
        intro = f'<p class="intro">{escape(t["intro"])}</p>' if t["intro"] else ""
        inner = f'{intro}{link}\n  <div class="list">\n{chr(10).join(cards)}\n  </div>'
        attrs = f'id="t-{t["key"]}" data-topic="{t["key"]}" data-kind="{kind}"'
        if kind == "main":
            main_html = f'<section class="topic" {attrs}>\n  <header class="topic-head">{head}</header>\n  {inner}\n</section>'
        elif kind in ("branch", "relax", "pool"):
            topics_html.append(f'<details class="topic branch" {attrs}>\n  <summary class="topic-head">{head}</summary>\n  {inner}\n</details>')
    tag = {"learn": "按需打开 · 看完自测", "pool": "自己挑 · 定期换新"}.get(z["key"], "不分先后 · 不计进度")
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
    "{{MAIN_N}}": str(len(steps_html)), "{{STEPS}}": "\n".join(steps_html),
    "{{TOC}}": "\n".join(toc_html), "{{MAINLINE}}": main_html, "{{ZONES}}": "\n".join(zones_html),
    "{{DATA}}": json.dumps(js_data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"),
}.items():
    page = page.replace(k, x)
(HERE / "index.html").write_text(page, encoding="utf-8")
print(f"index.html: {len(js_data)} videos, {sum(len(z['topics']) for z in data['zones'])} topics, main line {len(steps_html)} steps")
