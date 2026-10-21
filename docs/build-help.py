"""docs/help.md から使いかたページ(help.html)を作る

  python docs/build-help.py            → help.html(アプリと同じ場所に置くもの。画像は docs/screenshots を参照)
  python docs/build-help.py --embed X  → 画像を中に埋め込んだ1枚のページを X に書き出す

help.md を直したら、このスクリプトを実行して help.html を作り直してください。
必要なもの: Python 3 と markdown(pip install markdown)
"""
import base64, os, re, sys, unicodedata
import markdown
from markdown.extensions.toc import TocExtension

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def slug(value, sep='-'):
    v = value.strip().lower()
    v = ''.join(ch for ch in v if ch in ' -_' or unicodedata.category(ch)[0] in 'LN')
    return v.replace(' ', sep)


def build(embed_to=None):
    md_text = open(os.path.join(HERE, 'help.md'), encoding='utf-8').read()
    conv = markdown.Markdown(extensions=['tables', 'sane_lists', TocExtension(slugify=slug, toc_depth='2')])
    body = conv.convert(md_text)
    toc = [(t['id'], t['name']) for t in conv.toc_tokens[0]['children']] if conv.toc_tokens else []
    body = body.replace('<hr />', '')

    # 写真は2倍の細かさで撮ってあるので、表示は半分の大きさにする(小さい切り抜きが大きくなりすぎないように)
    def half_width(m):
        tag = m.group(0)
        src = re.search(r'src="(docs/screenshots/[^"]+\.png)"', tag)
        if not src or ' width=' in tag:
            return tag
        with open(os.path.join(ROOT, src.group(1)), 'rb') as f:
            head = f.read(24)
        w = int.from_bytes(head[16:20], 'big')
        return tag.replace('<img ', f'<img width="{w // 2}" ', 1)
    body = re.sub(r'<img [^>]*>', half_width, body)

    if embed_to:
        def emb(m):
            data = base64.b64encode(open(os.path.join(ROOT, m.group(1)), 'rb').read()).decode()
            return 'src="data:image/png;base64,' + data + '"'
        body = re.sub(r'src="(docs/screenshots/[^"]+\.png)"', emb, body)
    body = body.replace('<img ', '<img loading="lazy" decoding="async" ')
    nav = '\n'.join(f'<li><a href="#{i}">{n}</a></li>' for i, n in toc)

    back = '' if embed_to else '<a class="back" href="index.html">← アプリに戻る</a>'
    head_extra = '' if embed_to else '<link rel="icon" type="image/png" href="icons/favicon-64.png">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n<meta charset="utf-8">'
    page = TEMPLATE.replace('{{HEAD}}', head_extra).replace('{{BACK}}', back).replace('{{NAV}}', nav).replace('{{BODY}}', body)
    if not embed_to:
        page = '<!doctype html>\n<html lang="ja">\n<head>\n' + page.replace('<!--/head-->', '</head>\n<body>') + '\n</body>\n</html>\n'
        out = os.path.join(ROOT, 'help.html')
    else:
        page = page.replace('<!--/head-->', '')
        out = embed_to
    open(out, 'w', encoding='utf-8').write(page)
    print('作成しました:', out, f'({len(page)//1024}KB)')


TEMPLATE = r"""{{HEAD}}
<title>プロット帖 使いかた</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@400;500;700&family=Shippori+Mincho+B1:wght@700&display=swap">
<style>
/* Layout: sticky contents rail on the left (PC), one readable column on the app's dotted 原稿用紙 desk */
:root{
  --paper:#ECEFF4; --sheet:#FFFFFF; --sheet-2:#F6F8FB; --ink:#1A2030; --ink-2:#556074; --ink-3:#8791A3;
  --line:#D5DBE5; --dot:#C3CDDC; --blue:#2A66C9; --blue-soft:#E1EAF8;
  --f-ui:"Zen Kaku Gothic New","Hiragino Kaku Gothic ProN","Noto Sans JP","Yu Gothic",Meiryo,sans-serif;
  --f-title:"Shippori Mincho B1","Hiragino Mincho ProN","Yu Mincho",serif;
  color-scheme:light;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --paper:#11141B; --sheet:#1A1F29; --sheet-2:#202634; --ink:#E5E9F1; --ink-2:#A1AABB; --ink-3:#717B8E;
  --line:#2D3443; --dot:#2A3140; --blue:#76A6F0; --blue-soft:#1D2A42; color-scheme:dark;
}}
:root[data-theme="dark"]{
  --paper:#11141B; --sheet:#1A1F29; --sheet-2:#202634; --ink:#E5E9F1; --ink-2:#A1AABB; --ink-3:#717B8E;
  --line:#2D3443; --dot:#2A3140; --blue:#76A6F0; --blue-soft:#1D2A42; color-scheme:dark;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion: reduce){html{scroll-behavior:auto}}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--f-ui);font-size:15.5px;line-height:1.85;
  background-image:radial-gradient(var(--dot) 1px,transparent 1.2px);background-size:18px 18px;
  padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
.top{position:sticky;top:0;z-index:5;background:var(--sheet);border-bottom:1px solid var(--line);
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:10px;
  display:flex;align-items:center;gap:12px}
.logo{display:flex;align-items:center;gap:8px;font-weight:700;letter-spacing:.06em;white-space:nowrap}
.logo i{font-style:normal;width:22px;height:22px;border:2px solid var(--ink);border-radius:5px;display:grid;place-items:center;font-family:var(--f-title);font-size:12px;line-height:1}
.logo span{color:var(--ink-3);font-weight:500}
.back{margin-left:auto;text-decoration:none;color:var(--blue);border:1px solid var(--line);border-radius:8px;padding:5px 12px;font-size:13.5px;font-weight:500;white-space:nowrap;background:var(--sheet)}
.back:hover{border-color:var(--blue)}
.layout{max-width:1180px;margin:0 auto;display:grid;grid-template-columns:230px minmax(0,1fr);gap:28px;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:28px 80px}
nav{position:sticky;top:72px;align-self:start;max-height:calc(100vh - 92px);overflow:auto}
nav p{margin:0 0 8px;font-size:12px;color:var(--ink-3);letter-spacing:.12em}
nav ol{list-style:none;margin:0;padding:0;counter-reset:n}
nav li{counter-increment:n}
nav a{display:flex;gap:8px;padding:5px 10px;border-radius:7px;color:var(--ink-2);text-decoration:none;font-size:13.5px;line-height:1.5}
nav a::before{content:counter(n);color:var(--ink-3);font-variant-numeric:tabular-nums;min-width:1.4em;text-align:right}
nav a:hover{background:var(--sheet);color:var(--ink)}
nav a.on{background:var(--sheet);color:var(--ink);font-weight:700;box-shadow:inset 3px 0 0 var(--blue)}
details.mtoc{display:none}
article{background:var(--sheet);border:1px solid var(--line);border-radius:16px;padding:36px clamp(18px,5vw,56px) 48px;min-width:0;
  box-shadow:0 1px 2px rgba(18,28,48,.06),0 10px 30px rgba(18,28,48,.06)}
h1{font-family:var(--f-title);font-size:clamp(28px,5vw,38px);line-height:1.3;margin:0 0 14px;letter-spacing:.04em;text-wrap:balance}
h2{font-size:22px;margin:56px 0 12px;scroll-margin-top:76px;text-wrap:balance}
h2::before{content:"";display:block;width:36px;height:4px;border-radius:2px;background:var(--blue);margin-bottom:12px}
h3{font-size:17px;margin:30px 0 6px;scroll-margin-top:76px}
p{margin:10px 0}
a{color:var(--blue);text-underline-offset:3px}
ul,ol{padding-left:1.4em;margin:10px 0}
li{margin:4px 0}
li::marker{color:var(--ink-3)}
code{font-family:ui-monospace,Consolas,monospace;font-size:.88em;background:var(--sheet-2);border:1px solid var(--line);border-radius:5px;padding:1px 6px}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:14.5px;display:block;overflow-x:auto}
th,td{border-bottom:1px solid var(--line);padding:8px 12px;text-align:left;vertical-align:top}
th{font-size:12.5px;color:var(--ink-2);letter-spacing:.04em;font-weight:500;border-bottom-width:2px}
article img{display:block;max-width:100%;height:auto;margin:16px 0 22px;border-radius:10px;border:1px solid var(--line);box-shadow:0 6px 20px rgba(18,28,48,.10)}
article p:has(> img ~ img){display:flex;flex-wrap:wrap;gap:14px}
article p:has(> img ~ img) img{width:calc((100% - 28px) / 3);margin:6px 0}
article img[width]{width:auto}
@media (max-width:900px){
  .layout{grid-template-columns:minmax(0,1fr);padding-top:16px}
  nav{display:none}
  details.mtoc{display:block;background:var(--sheet);border:1px solid var(--line);border-radius:12px;padding:10px 14px;margin-bottom:12px}
  details.mtoc summary{cursor:pointer;font-weight:700}
  details.mtoc ol{margin:8px 0 4px;padding-left:1.6em;font-size:14.5px}
  details.mtoc a{display:block;padding:3px 0;text-decoration:none}
  article{border-radius:12px;padding-top:26px}
  body{font-size:15px}
}
@media (max-width:640px){ article p:has(> img ~ img) img{width:100%} }
</style>
<!--/head-->
<header class="top">
  <div class="logo"><i aria-hidden="true">帖</i>プロット帖<span>使いかた</span></div>
  {{BACK}}
</header>
<div class="layout">
  <nav aria-label="もくじ"><p>もくじ</p><ol>
{{NAV}}
  </ol></nav>
  <main>
    <details class="mtoc"><summary>もくじ</summary><ol>
{{NAV}}
    </ol></details>
    <article>
{{BODY}}
    </article>
  </main>
</div>
<script>
// アプリで選んだ明るさ(ライト/ダーク)に合わせる
try{ var t=JSON.parse(localStorage.getItem('plotcho.theme')||'null'); if(t==='light'||t==='dark') document.documentElement.setAttribute('data-theme',t); }catch(e){}
// いま読んでいる項目をもくじで示す
(function(){
  var links=[].slice.call(document.querySelectorAll('nav a'));
  var map={}; links.forEach(function(a){ map[a.getAttribute('href').slice(1)]=a; });
  if(!('IntersectionObserver' in window)) return;
  var io=new IntersectionObserver(function(es){
    es.forEach(function(e){ if(e.isIntersecting){ links.forEach(function(a){a.classList.remove('on');}); var a=map[e.target.id]; if(a) a.classList.add('on'); } });
  },{rootMargin:'-80px 0px -70% 0px'});
  document.querySelectorAll('article h2[id]').forEach(function(h){ io.observe(h); });
  document.querySelectorAll('details.mtoc a').forEach(function(a){ a.addEventListener('click',function(){ a.closest('details').open=false; }); });
})();
</script>"""

if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '--embed':
        build(embed_to=sys.argv[2])
    else:
        build()
