#!/usr/bin/env python3
"""
Markdown 转 HTML 转换器
版本: 3.0.5
纯 JS + CSS transform 实现滚轮缩放 + 左键拖动（无第三方库）
"""

import argparse, re, os, sys, subprocess

# ─── 共享 pan/zoom JS（注入到每个HTML）────────────────────────────────────────

PAN_ZOOM = r'''
<script>
(function() {
  var wrap, inner, isDragging = false, lastX = 0, lastY = 0;
  var scale = 1, tx = 0, ty = 0;

  function getWrap() {
    wrap = document.getElementById('diagram-wrap');
    inner = document.getElementById('diagram-inner');
    if (!wrap || !inner) return;
    reset();
    wrap.addEventListener('mousedown', function(e) {
      if (e.button === 0) { isDragging = true; lastX = e.clientX; lastY = e.clientY; wrap.style.cursor = 'grabbing'; }
    });
    document.addEventListener('mousemove', function(e) {
      if (!isDragging) return;
      tx += e.clientX - lastX; ty += e.clientY - lastY; lastX = e.clientX; lastY = e.clientY;
      clamp(); apply();
    });
    document.addEventListener('mouseup', function() { isDragging = false; wrap.style.cursor = 'grab'; });
    wrap.addEventListener('wheel', function(e) {
      e.preventDefault();
      var mx = e.clientX, my = e.clientY;
      var ns = Math.max(0.05, Math.min(50, scale * (e.deltaY < 0 ? 1.1 : 0.9)));
      tx = mx - (mx - tx) * ns / scale; ty = my - (my - ty) * ns / scale; scale = ns;
      clamp(); apply();
    }, { passive: false });
    // 双击重置
    wrap.addEventListener('dblclick', reset);
    // 触摸
    var lastDist = 0, lastMidX = 0, lastMidY = 0;
    wrap.addEventListener('touchstart', function(e) {
      if (e.touches.length === 1) { isDragging = true; lastX = e.touches[0].clientX; lastY = e.touches[0].clientY; }
      else if (e.touches.length === 2) {
        lastDist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
        lastMidX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
        lastMidY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      }
    }, { passive: false });
    wrap.addEventListener('touchmove', function(e) {
      e.preventDefault();
      if (e.touches.length === 1 && isDragging) {
        tx += e.touches[0].clientX - lastX; ty += e.touches[0].clientY - lastY;
        lastX = e.touches[0].clientX; lastY = e.touches[0].clientY;
        clamp(); apply();
      } else if (e.touches.length === 2) {
        var d = Math.hypot(e.touches[0].clientX - e.touches[1].clientX, e.touches[0].clientY - e.touches[1].clientY);
        if (lastDist > 0) {
          var ns = Math.max(0.05, Math.min(50, scale * d / lastDist));
          tx = lastMidX - (lastMidX - tx) * ns / scale; ty = lastMidY - (lastMidY - ty) * ns / scale; scale = ns;
          clamp(); apply();
        }
        lastDist = d; lastMidX = (e.touches[0].clientX + e.touches[1].clientX) / 2; lastMidY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
      }
    }, { passive: false });
    wrap.addEventListener('touchend', function() { isDragging = false; lastDist = 0; });
    window.addEventListener('resize', reset);
  window._pzReset = reset; // 供外部回调（如mermaid/vega渲染后重置）
  }

  function reset() {
    var vw = window.innerWidth, vh = window.innerHeight;
    var cw = inner.offsetWidth, ch = inner.offsetHeight;
    if (cw === 0 || ch === 0) { cw = vw; ch = vh; }
    scale = Math.min(vw / cw, vh / ch, 1) * 0.95;
    tx = (vw - cw * scale) / 2;
    ty = (vh - ch * scale) / 2;
    apply();
  }

  function clamp() {
    var vw = window.innerWidth, vh = window.innerHeight;
    var cw = inner.offsetWidth, ch = inner.offsetHeight;
    tx = Math.max(vw - cw * scale, Math.min(0, tx));
    ty = Math.max(vh - ch * scale, Math.min(0, ty));
  }

  function apply() {
    inner.style.transform = 'translate(' + tx + 'px,' + ty + 'px) scale(' + scale + ')';
    inner.style.transformOrigin = '0 0';
    var el = document.getElementById('hint');
    if (el) el.textContent = Math.round(scale * 100) + '%　双击重置　滚轮缩放　左键拖动';
  }

  document.addEventListener('DOMContentLoaded', getWrap);
})();
</script>'''

CSS_BASE = '''
<style>
* { margin: 0; padding: 0; box-sizing: border-box; -webkit-user-select: none; user-select: none; }
html, body { width: 100%; height: 100%; overflow: hidden; background: #1e1e1e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
#diagram-wrap { width: 100vw; height: 100vh; overflow: hidden; cursor: grab; position: relative; }
#diagram-wrap:active { cursor: grabbing; }
#diagram-inner { position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; will-change: transform; pointer-events: none; }
#diagram-inner > * { pointer-events: auto; }
#diagram-header { position: absolute; top: 0; left: 0; right: 0; z-index: 10; padding: 12px 16px; background: linear-gradient(to bottom, rgba(20,20,20,0.92), transparent); display: flex; align-items: center; gap: 10px; pointer-events: none; }
#diagram-header h1 { color: #e0e0e0; font-size: 15px; font-weight: normal; }
.badge { padding: 3px 10px; border-radius: 4px; font-size: 11px; flex-shrink: 0; }
.b-ok { background: rgba(34,197,94,0.9); color: white; }
.b-warn { background: rgba(249,115,22,0.9); color: white; }
.b-info { background: rgba(59,130,246,0.9); color: white; }
#hint { position: absolute; bottom: 10px; right: 10px; background: rgba(0,0,0,0.5); color: #aaa; font-size: 11px; padding: 4px 10px; border-radius: 4px; pointer-events: none; }
#diagram-inner svg { display: block; }
#diagram-inner img { max-width: 90vw; max-height: 90vh; }
</style>'''


# ─── 通用 HTML 外壳 ─────────────────────────────────────────────────────────

def wrap_html(title, badge_html, inner_html, extra_css=''):
    """通用 HTML 外壳，inner_html 直接插入 inner div 中"""
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{title}</title>
{CSS_BASE}{extra_css}
</head>
<body>
<div id="diagram-wrap">
  <div id="diagram-header">
    <h1>{title}</h1>
    {badge_html}
  </div>
  <div id="diagram-inner">{inner_html}</div>
  <div id="hint">100%　双击重置　滚轮缩放　左键拖动</div>
</div>
{PAN_ZOOM}
</body>
</html>'''


# ─── PlantUML ─────────────────────────────────────────────────────────────────

def plantuml_encode(s):
    import base64, zlib
    return base64.b64encode(zlib.compress(bytes(s, 'utf-8'))[2:-4]).decode('utf-8')


def build_plantuml_html(content: str, name: str) -> str:
    match = re.search(r'```plantuml\s*\n(.*?)```', content, re.DOTALL)
    if not match:
        match = re.search(r'```puml\s*\n(.*?)```', content, re.DOTALL)
    puml_code = match.group(1).strip() if match else ''

    badge = '<span class="badge b-ok">✅ SVG</span>'
    svg_or_img = ''
    if puml_code:
        try:
            result = subprocess.run(
                ['plantuml', '-tsvg', '-p'],
                input=puml_code.encode('utf-8'),
                capture_output=True, timeout=30
            )
            if result.returncode == 0 and result.stdout:
                svg_raw = result.stdout.decode('utf-8')
                # 清理PlantUML的固定宽高和破坏等比的属性
                svg_raw = re.sub(r'\s+width="[^"]*"', '', svg_raw)
                svg_raw = re.sub(r'\s+height="[^"]*"', '', svg_raw)
                svg_raw = re.sub(r'\s+style="[^"]*"', '', svg_raw)
                svg_raw = re.sub(r'preserveAspectRatio="[^"]*"',
                                 'preserveAspectRatio="xMidYMid meet"', svg_raw)
                svg_or_img = svg_raw
            else:
                err = (result.stderr.decode('utf-8') or 'unknown')[:60]
                badge = f'<span class="badge b-warn">⚠️ 本地失败 {err}</span>'
                enc = plantuml_encode(puml_code)
                svg_or_img = f'<img src="http://www.plantuml.com/plantuml/svg/{enc}"/>'
        except FileNotFoundError:
            badge = '<span class="badge b-warn">⚠️ PlantUML未安装</span>'
            enc = plantuml_encode(puml_code)
            svg_or_img = f'<img src="http://www.plantuml.com/plantuml/svg/{enc}"/>'
        except Exception as e:
            badge = f'<span class="badge b-warn">⚠️ {str(e)[:50]}</span>'
            enc = plantuml_encode(puml_code)
            svg_or_img = f'<img src="http://www.plantuml.com/plantuml/svg/{enc}"/>'

    html = wrap_html(name, badge, svg_or_img)
    return html


# ─── Mermaid ──────────────────────────────────────────────────────────────────

def build_mermaid_html(content: str, name: str) -> str:
    match = re.search(r'```mermaid\s*\n(.*?)```', content, re.DOTALL)
    mermaid_code = match.group(1).strip() if match else ''
    esc = mermaid_code.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
    badge = '<span class="badge b-info">🌐 需要网络</span>'
    extra = '<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>\n<script>mermaid.initialize({startOnLoad:false,theme:"dark"});mermaid.run().then(function(){if(window._pzReset)window._pzReset();});</script>'
    return wrap_html(name, badge, f'<div class="mermaid">{esc}</div>', extra)


# ─── Pure HTML ───────────────────────────────────────────────────────────────

HTML_BG_CSS = '''
<style>
html, body { background: #f0f4f8; }
#diagram-header { background: linear-gradient(to bottom, rgba(240,244,248,0.95), transparent); }
#diagram-header h1 { color: #333; }
#hint { color: #888; }
</style>'''

def build_pure_html(content: str, name: str) -> str:
    match = re.search(r'(<div style="width:.*)', content, re.DOTALL)
    if not match:
        return f'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{name}</title></head><body><pre>{content}</pre></body></html>'
    html_block = match.group(1)
    depth = html_block.count('<div') - 1
    end_pos, search_from = 0, 0
    for _ in range(depth):
        idx = html_block.find('</div>', search_from)
        if idx == -1:
            break
        end_pos = idx + 6
        search_from = idx + 6
    if end_pos > 0:
        html_block = html_block[:end_pos]
    style_match = re.search(r'<style scoped>(.*?)</style>', content, re.DOTALL)
    style_content = style_match.group(1) if style_match else ''
    badge = '<span class="badge b-info">架构图</span>'
    extra = (HTML_BG_CSS + f'<style>{style_content}</style>') if style_content else HTML_BG_CSS
    return wrap_html(name, badge, html_block, extra)


# ─── Vega ─────────────────────────────────────────────────────────────────────

def build_vega_html(content: str, name: str) -> str:
    match = re.search(r'```(?:vega-lite|vega)\s*\n(.*?)```', content, re.DOTALL)
    vega_json = match.group(1).strip() if match else '{}'
    esc = vega_json.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
    badge = '<span class="badge b-info">🌐 需要网络</span>'
    extra = ('''<script src="https://cdn.jsdelivr.net/npm/vega@5/build/vega.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5/build/vega-lite.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6/build/vega-embed.min.js"></script>
<script>
var spec = JSON.parse('{esc}');
vegaEmbed('#vis', spec, {{actions:{{export:true,source:false,editor:false}}}}).then(function(){{if(window._pzReset)window._pzReset();}}).catch(console.error);
</script>''')
    return wrap_html(name, badge, '<div id="vis"></div>', extra)


# ─── Infographic ─────────────────────────────────────────────────────────────

def build_infographic_html(content: str, name: str, input_path: str) -> str:
    png_path = input_path.replace('.md', '_截图.png')
    png_name = os.path.basename(png_path)
    badge = '<span class="badge b-info">PNG截图</span>'
    if os.path.exists(png_path):
        return wrap_html(name, badge, f'<img src="{png_name}" alt="{name}"/>')
    else:
        body = f'<div style="background:#1e1e1e;padding:20px;"><h1 style="color:#e0e0e0;">{name}</h1><p style="color:#aaa;margin-top:10px;">PNG截图不存在，请查看同目录截图文件</p></div>'
        return f'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{name}</title></head><body>{body}</body></html>'


# ─── Canvas ──────────────────────────────────────────────────────────────────

def build_canvas_html(content: str, name: str) -> str:
    match = re.search(r'```canvas\s*\n(.*?)\n```', content, re.DOTALL)
    canvas_json = match.group(1).strip() if match else '{}'
    esc = canvas_json.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
    body = f'''<div style="background:#1e1e1e;padding:20px;height:100vh;">
<div id="diagram-header"><h1>{name}</h1><span class="badge b-info">Canvas 需 Obsidian 渲染</span></div>
<pre style="background:rgba(45,45,45,0.95);border-radius:8px;padding:16px;color:#d4d4d4;white-space:pre-wrap;font-size:12px;margin-top:60px;overflow:auto;height:calc(100vh-100px);">{esc}</pre>
</div>'''
    return f'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>{name}</title></head><body>{body}</body></html>'


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='将含图 .md 转换为可双击的 .html（纯JS缩放拖动）')
    parser.add_argument('--input', '-i', required=True)
    parser.add_argument('--output', '-o')
    args = parser.parse_args()
    success = md_to_html(args.input, args.output)
    sys.exit(0 if success else 1)


def md_to_html(input_path: str, output_path: str = None) -> bool:
    if output_path is None:
        output_path = input_path.rstrip('.md') + '.html'
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"读取文件失败: {e}", file=sys.stderr)
        return False
    name = os.path.basename(input_path).replace('.md', '')
    if '```plantuml' in content or '@startuml' in content:
        html = build_plantuml_html(content, name)
    elif '```mermaid' in content:
        html = build_mermaid_html(content, name)
    elif '<div' in content and 'style=' in content:
        html = build_pure_html(content, name)
    elif '```vega' in content or '```vega-lite' in content:
        html = build_vega_html(content, name)
    elif '```infographic' in content:
        html = build_infographic_html(content, name, input_path)
    elif '```canvas' in content or '"nodes":' in content:
        html = build_canvas_html(content, name)
    else:
        print(f"无法识别的图表类型: {input_path}", file=sys.stderr)
        return False
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ 已转换: {output_path}")
        return True
    except Exception as e:
        print(f"写入文件失败: {e}", file=sys.stderr)
        return False

if __name__ == '__main__':
    main()
