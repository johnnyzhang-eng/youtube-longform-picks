"""Build index.html from videos.json.  Usage: python3 build.py"""
import json
from html import escape
from pathlib import Path

HERE = Path(__file__).parent
SIGNALS = ["来源", "推荐", "主题", "时效"]
REPO = "https://github.com/johnnyzhang-eng/youtube-longform-picks"
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
    parts = ""
    if v.get("parts"):
        detail = " · ".join(f"{n} {p}" for n, p in zip(SIGNALS, v["parts"]))
        parts = f'<p class="parts"><b>{v["score"]} 分</b>{detail}</p>'
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
    {parts}
    <p class="ask"><b aria-label="带着问题看" title="带着问题看">问</b><span>{escape(v['ask'])}</span></p>
    {supply}
    {points}
    <div class="actions js-only">
      <button type="button" class="btn primary" data-open>看和记</button>
      <button type="button" class="btn" data-seen aria-pressed="false">标记已看</button>
    </div>
  </div>
</article>"""


def how_row(c):
    m = c["seconds"] // 60
    dur = f"{m // 60} 小时 {m % 60} 分" if m >= 60 else f"{m} 分"
    extra = (f' · Hacker News {c["hn"]} 分' if c["hn"] else "") + (f' · <em>{escape(c["reason"])}</em>' if c["reason"] else "")
    if c["parts"]:
        detail = " + ".join(f"{n} {p}" for n, p in zip(SIGNALS, c["parts"]))
        segs = "".join(f'<i class="s{i + 1}" style="width:{p}%"></i>' for i, p in enumerate(c["parts"]) if p)
        viz = f'<span class="track" title="{detail}">{segs}</span><b class="tot">{c["score"]}</b>'
    else:
        viz = '<span class="track none"></span><b class="tot">–</b>'
    return (f'<li class="row{"" if c["picked"] else " out"}"><span class="rt"><a href="https://www.youtube.com/watch?v={c["id"]}" target="_blank" rel="noopener">'
            f'{escape(c["title"])}</a><small>{escape(c["channel"])} · {dur}{extra}</small></span>{viz}</li>')


def how_html(rd):
    cfg, cs = rd["config"], rd["candidates"]
    scored = sorted((c for c in cs if c["parts"]), key=lambda c: c["date"], reverse=True)
    scored.sort(key=lambda c: (-c["score"], -c["hn"]))
    picked = [c for c in scored if c["picked"]]
    rest = [c for c in scored if not c["picked"]] + [c for c in cs if not c["parts"]]
    src, en, tp, fr = cfg["source"], cfg["endorse"], cfg["topic"], cfg["fresh"]
    w = [src["A"], en[0][1], tp["2"], fr["durable"]]
    sbar = "".join(f'<span class="s{i + 1}" style="flex:{x}"><em>{n} </em>{x}</span>' for i, (n, x) in enumerate(zip(SIGNALS, w)))
    legend = "".join(f'<span><i class="dot s{i + 1}"></i>{n}</span>' for i, n in enumerate(SIGNALS))
    st = fr["status"]
    hi, lo = cfg["max_seconds"] // 60, cfg["min_seconds"] // 60
    return f"""<section class="how" id="how">
  <h2>我们怎么选片</h2>
  <p class="how-lede">每个候选视频先过门槛，再按 4 个信号打分，满分 100。{cfg['threshold']} 分以上进候选池。下面是完整的算法，和第 {rd['round']} 期每个候选的得分。</p>

  <h3>打分：4 个信号，满分 {sum(w)}</h3>
  <div class="sbar" aria-hidden="true">{sbar}</div>
  <div class="sig">
    <div><h4><i class="dot s1"></i>来源<small>最高 {w[0]}</small></h4><p>作者过去的表现，最能预测下一个视频的质量。</p>
      <dl><dt>A 档频道</dt><dd>{src['A']}</dd><dt>B 档频道</dt><dd>{src['B']}</dd><dt>白名单之外</dt><dd>0</dd></dl></div>
    <div><h4><i class="dot s2"></i>推荐<small>最高 {w[1]}</small></h4><p>陌生的来源，靠内行的认可进来。它和来源同分，所以白名单之外的好视频不会被挡住。</p>
      <dl><dt>Hacker News {en[0][0]} 分以上</dt><dd>{en[0][1]}</dd><dt>{en[1][0]}–{en[0][0] - 1} 分</dt><dd>{en[1][1]}</dd><dt>{en[2][0]}–{en[1][0] - 1} 分</dt><dd>{en[2][1]}</dd><dt>没有</dt><dd>0</dd></dl>
      <p class="fine"><b>Hacker News 是什么：</b>美国创业孵化器 Y Combinator 办的技术社区（<a href="https://news.ycombinator.com" target="_blank" rel="noopener">news.ycombinator.com</a>）。程序员、研究者和创业者在上面提交链接、互相投票，分数大致就是得票数。一个视频在那里拿到高分，说明很多内行觉得它值得看。</p></div>
    <div><h4><i class="dot s3"></i>主题<small>最高 {w[2]}</small></h4><p>再好的视频，和关心的方向无关，也不占位置。</p>
      <dl><dt>核心方向</dt><dd>{tp['2']}</dd><dt>相邻方向</dt><dd>{tp['1']}</dd><dt>无关</dt><dd>出局</dd></dl>
      <p class="fine">核心：AI 原理与方法、数学、数据工程、认知与学习、思维模型。相邻：其他科学和工程、编程、人物与历史。</p></div>
    <div><h4><i class="dot s4"></i>时效<small>最高 {w[3]}</small></h4><p>要么不会过时，要么足够新。</p>
      <dl><dt>原理、历史、方法讲解，不看年份</dt><dd>{fr['durable']}</dd><dt>现状和做法，{st[0][0]} 天内</dt><dd>{st[0][1]}</dd><dt>{st[1][0]} 天内</dt><dd>{st[1][1]}</dd><dt>{st[2][0]} 天内</dt><dd>{st[2][1]}</dd><dt>更早</dt><dd>出局</dd></dl></div>
  </div>
  <p class="fb"><b>第 5 个信号：看完的反馈，±10。</b>看完觉得值的频道加分，总被跳过的减分。位置留好了，现在还没有数据，全部按 0 算。</p>

  <div class="rules">
    <div><h3>门槛：不过直接出局</h3><p class="chips2"><span>能正常播放</span><span>{lo} 分钟到 {hi // 60} 小时 {hi % 60} 分</span><span>和主题有关</span><span>谈现状的不超过 {st[2][0]} 天</span><span>库里还没有</span></p></div>
    <div><h3>入选</h3><p class="chips2"><span>总分 ≥ {cfg['threshold']}</span><span>每个频道最多 {cfg['per_channel']} 个</span><span>同分时推荐分高的在前，再看谁更新</span><span>池子最多 {cfg['pool_cap']} 个</span></p></div>
    <div><h3>不计分</h3><p class="chips2 no"><span>播放量</span><span>点赞数</span><span>关键词出现次数</span><span>时长长短</span></p></div>
  </div>

  <h3>第 {rd['round']} 期：每个候选的得分</h3>
  <p class="flow"><span><b>{rd['collected']}</b> 个收集到</span><i>→</i><span><b>{len(cs)}</b> 个够长、能播放</span><i>→</i><span><b>{len(scored)}</b> 个进入打分</span><i>→</i><span><b>{len(picked)}</b> 个入选</span></p>
  <p class="legend">{legend}<span><i class="cutmark"></i>竖线是 {cfg['threshold']} 分</span><span>{rd['date']}，来源是白名单频道近 {rd['window_days']} 天的新视频和 Hacker News 上 {en[2][0]} 分以上的链接</span></p>
  <ol class="chart" style="--cut:{cfg['threshold']}%">
{chr(10).join(how_row(c) for c in picked)}
  </ol>
  <details class="outs"><summary>没入选的 {len(rest)} 个，和各自的原因</summary>
  <ol class="chart" style="--cut:{cfg['threshold']}%">
{chr(10).join(how_row(c) for c in rest)}
  </ol></details>

  <h3>新视频和老视频</h3>
  <p>AI 变化很快，所以“时效”这一项把内容分成两类，不是只看发布日期。</p>
  <div class="age">
    <div class="keep"><b>不会过时，老的照样收</b><ul><li>原理：神经网络怎么学习、注意力机制、数据库怎么存数据</li><li>历史和发展过程</li><li>新技术、新方法的讲解</li></ul></div>
    <div class="drop"><b>会过时，只收近期的</b><ul><li>某个工具怎么用、提示词技巧</li><li>谈“现在 AI 到了哪一步”的访谈</li><li>对行业的预测</li></ul></div>
  </div>
  <p>所以这里能看到 2017 年讲神经网络的视频，却看不到 2024 年谈 AI 现状的播客。</p>

  <h3>频道分档</h3>
  <p>A 档以讲解和课程为主，内容经得起核对。B 档以访谈和行业内容为主，质量要看单期。</p>
  <p class="wl"><b>A 档</b>：{"、".join(escape(x) for x in cfg['tiers']['A'])}<br><b>B 档</b>：{"、".join(escape(x) for x in cfg['tiers']['B'])}</p>

  <h3>要说清楚的</h3>
  <ul>
    <li>一个视频属于哪个主题、算“原理”还是“现状”，是 AI 看标题和简介判断的。每个视频的判断、分数和落选原因都在<a href="{REPO}/blob/main/pool/round-{rd['round']:02d}.json" target="_blank" rel="noopener">这一期的数据文件</a>里，打分脚本是 <a href="{REPO}/blob/main/tools/score.py" target="_blank" rel="noopener">tools/score.py</a>。</li>
    <li>选片的是 AI（Opus 和 Fable），Codex 和 Kimi 审过一轮。它们没有逐个看完视频。</li>
    <li>权重是按第 1 期校准的初始值。来源现在只有白名单频道和 Hacker News，心理学类的还不够。</li>
    <li>学习主线不走这套打分：它的问题和参考要点逐条对照过作者公开的讲义。</li>
  </ul>
  <p>觉得哪个权重不对，或者有更好的信号，欢迎到 <a href="{REPO}/issues/7" target="_blank" rel="noopener">GitHub 上的讨论</a>里说。接下来打算每周自动跑一次这套算法。</p>
</section>"""


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

rd = json.loads((HERE / "pool" / next(z["round"]["file"] for z in data["zones"] if z.get("round"))).read_text(encoding="utf-8"))
page = (HERE / "template.html").read_text(encoding="utf-8")
for k, x in {
    "{{UPDATED}}": data["updated"], "{{TOTAL}}": str(len(js_data)),
    "{{HOW}}": how_html(rd),
    "{{MAIN_N}}": str(len(steps_html)), "{{STEPS}}": "\n".join(steps_html),
    "{{TOC}}": "\n".join(toc_html), "{{MAINLINE}}": main_html, "{{ZONES}}": "\n".join(zones_html),
    "{{DATA}}": json.dumps(js_data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"),
}.items():
    page = page.replace(k, x)
(HERE / "index.html").write_text(page, encoding="utf-8")
print(f"index.html: {len(js_data)} videos, {sum(len(z['topics']) for z in data['zones'])} topics, main line {len(steps_html)} steps")
