#!/usr/bin/env python3
"""
Markdown 转 HTML 转换器
版本: 3.0.4
将含 PlantUML / HTML / Mermaid / Vega / Canvas / Infographic 的 .md 转换为可双击的 .html
特性：全屏图 + 滚轮缩放 + 左键拖动平移，原比例不变形
"""

import argparse, re, os, sys, subprocess

# ─── CLI ──────────────────────────────────────────────────────────────────────

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


# ─── PlantUML ─────────────────────────────────────────────────────────────────

def plantuml_encode(s):
    import base64, zlib
    return base64.b64encode(zlib.compress(bytes(s, 'utf-8'))[2:-4]).decode('utf-8')


def build_plantuml_html(content: str, name: str) -> str:
    match = re.search(r'```plantuml\s*\n(.*?)```', content, re.DOTALL)
    if not match:
        match = re.search(r'```puml\s*\n(.*?)```', content, re.DOTALL)
    puml_code = match.group(1).strip() if match else ''

    svg_block = ''
    note = '<span class="note ok">✅ 本地SVG渲染成功</span>'
    if puml_code:
        try:
            result = subprocess.run(
                ['plantuml', '-tsvg', '-p'],
                input=puml_code.encode('utf-8'),
                capture_output=True, timeout=30
            )
            if result.returncode == 0 and result.stdout:
                svg_raw = result.stdout.decode('utf-8')
                # 清理SVG：去掉固定宽高/内联style，强制等比
                svg_raw = re.sub(r'\s+width="[^"]*"', '', svg_raw)
                svg_raw = re.sub(r'\s+height="[^"]*"', '', svg_raw)
                svg_raw = re.sub(r'\s+style="[^"]*"', '', svg_raw)
                svg_raw = re.sub(r'preserveAspectRatio="[^"]*"',
                                 'preserveAspectRatio="xMidYMid meet"', svg_raw)
                svg_block = svg_raw
            else:
                err = (result.stderr.decode('utf-8') or 'unknown')[:60]
                note = f'<span class="note warn">⚠️ 本地失败：{err}</span>'
                enc = plantuml_encode(puml_code)
                svg_block = f'<img src="http://www.plantuml.com/plantuml/svg/{enc}" class="diagram-img" onerror="this.parent__outer.innerHTML=\'<p class=err>⚠️ 渲染失败</p>\'"/>'
        except FileNotFoundError:
            note = '<span class="note warn">⚠️ PlantUML未安装，改为在线渲染（需网络）</span>'
            enc = plantuml_encode(puml_code)
            svg_block = f'<img src="http://www.plantuml.com/plantuml/svg/{enc}" class="diagram-img"/>'
        except Exception as e:
            note = f'<span class="note warn">⚠️ 异常：{str(e)[:50]}</span>'
            enc = plantuml_encode(puml_code)
            svg_block = f'<img src="http://www.plantuml.com/plantuml/svg/{enc}" class="diagram-img"/>'

    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{name}</title>
<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: 100%; height: 100%; overflow: hidden; background: #1e1e1e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
.wrap {{ width: 100vw; height: 100vh; overflow: hidden; cursor: grab; position: relative; }}
.wrap:active {{ cursor: grabbing; }}
.inner {{ display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; }}
.header {{ position: absolute; top: 0; left: 0; right: 0; z-index: 10; padding: 12px 16px; background: linear-gradient(to bottom, rgba(30,30,30,0.95), transparent); display: flex; align-items: center; gap: 10px; pointer-events: none; }}
h1 {{ color: #e0e0e0; font-size: 16px; font-weight: normal; }}
.note {{ padding: 3px 10px; border-radius: 4px; font-size: 11px; }}
.note.ok {{ background: rgba(34,197,94,0.9); color: white; }}
.note.warn {{ background: rgba(249,115,22,0.9); color: white; }}
.inner svg {{ max-width: 95vw; max-height: 95vh; display: block; }}
.inner img.diagram-img {{ max-width: 95vw; max-height: 95vh; border-radius: 4px; }}
.hint {{ position: absolute; bottom: 12px; right: 12px; background: rgba(0,0,0,0.55); color: #aaa; font-size: 11px; padding: 5px 10px; border-radius: 4px; pointer-events: none; }}
.err {{ color: #f48771; padding: 20px; font-size: 14px; }}
</style>
</head>
<body>
<div class="wrap" id="wrap">
  <div class="header">
    <h1>{name}</h1>
    {note}
  </div>
  <div class="inner">
    {svg_block}
  </div>
  <div class="hint">滚轮缩放 · 左键拖动平移</div>
</div>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  var wrap = document.getElementById('wrap');
  var svg = wrap.querySelector('svg');
  if (svg) {{
    svgPanZoom(svg, {{
      viewportId: 'diagram-viewport',
      zoomEnabled: true,
      panEnabled: true,
      controlIconsEnabled: false,
      fit: true,
      center: true,
      zoomScaleSensitivity: 0.5,
      minZoom: 0.1,
      maxZoom: 50,
      // 关键：事件绑定在svg上，但移动的是svg的transform
      eventsListener: function(e) {{
        // 确保鼠标事件能穿透header到达svg
        return true;
      }}
    }});
  }}
  // 图片降级方案也挂上panzoom
  var img = wrap.querySelector('img.diagram-img');
  if (img) {{
    svgPanZoom(img, {{
      viewportId: 'diagram-viewport',
      zoomEnabled: true,
      panEnabled: true,
      controlIconsEnabled: false,
      fit: true,
      center: true,
      zoomScaleSensitivity: 0.5,
      minZoom: 0.1,
      maxZoom: 50
    }});
  }}
}});
</script>
</body>
</html>'''


# ─── Mermaid ──────────────────────────────────────────────────────────────────

def build_mermaid_html(content: str, name: str) -> str:
    match = re.search(r'```mermaid\s*\n(.*?)```', content, re.DOTALL)
    mermaid_code = match.group(1).strip() if match else ''
    esc = mermaid_code.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{name}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: 100%; height: 100%; overflow: hidden; background: #1e1e1e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
.wrap {{ width: 100vw; height: 100vh; overflow: hidden; cursor: grab; position: relative; }}
.wrap:active {{ cursor: grabbing; }}
.inner {{ display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; }}
.header {{ position: absolute; top: 0; left: 0; right: 0; z-index: 10; padding: 12px 16px; background: linear-gradient(to bottom, rgba(30,30,30,0.95), transparent); display: flex; align-items: center; gap: 10px; pointer-events: none; }}
h1 {{ color: #e0e0e0; font-size: 16px; font-weight: normal; }}
.note {{ padding: 3px 10px; border-radius: 4px; font-size: 11px; background: rgba(59,130,246,0.9); color: white; }}
.inner svg {{ max-width: 90vw; max-height: 90vh; }}
.hint {{ position: absolute; bottom: 12px; right: 12px; background: rgba(0,0,0,0.55); color: #aaa; font-size: 11px; padding: 5px 10px; border-radius: 4px; pointer-events: none; }}
</style>
</head>
<body>
<div class="wrap" id="wrap">
  <div class="header">
    <h1>{name}</h1>
    <span class="note">🌐 需要网络</span>
  </div>
  <div class="inner">
    <div class="mermaid">{esc}</div>
  </div>
  <div class="hint">滚轮缩放 · 左键拖动平移</div>
</div>
<script>
mermaid.initialize({{ startOnLoad: false, theme: 'dark' }});
mermaid.run().then(function() {{
  var svg = document.querySelector('.mermaid svg');
  if (svg) {{
    svgPanZoom(svg, {{
      viewportId: 'diagram-viewport',
      zoomEnabled: true, panEnabled: true, controlIconsEnabled: false,
      fit: true, center: true, zoomScaleSensitivity: 0.5,
      minZoom: 0.05, maxZoom: 50
    }});
  }}
}});
</script>
</body>
</html>'''


# ─── Pure HTML (架构图等) ──────────────────────────────────────────────────────

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
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{name}</title>
<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: 100%; height: 100%; overflow: hidden; background: #f0f4f8; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
.wrap {{ width: 100vw; height: 100vh; overflow: hidden; cursor: grab; position: relative; }}
.wrap:active {{ cursor: grabbing; }}
.inner {{ display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; }}
.inner svg {{ max-width: 95vw; max-height: 95vh; }}
.header {{ position: absolute; top: 0; left: 0; right: 0; z-index: 10; padding: 12px 16px; background: linear-gradient(to bottom, rgba(240,244,248,0.95), transparent); display: flex; align-items: center; gap: 10px; pointer-events: none; }}
h1 {{ color: #333; font-size: 16px; font-weight: normal; }}
.note {{ padding: 3px 10px; border-radius: 4px; font-size: 11px; background: rgba(59,130,246,0.9); color: white; }}
.hint {{ position: absolute; bottom: 12px; right: 12px; background: rgba(0,0,0,0.4); color: #aaa; font-size: 11px; padding: 5px 10px; border-radius: 4px; pointer-events: none; }}
{style_content}
</style>
</head>
<body>
<div class="wrap" id="wrap">
  <div class="header">
    <h1>{name}</h1>
    <span class="note">架构图</span>
  </div>
  <div class="inner">
    {html_block}
  </div>
  <div class="hint">滚轮缩放 · 左键拖动平移</div>
</div>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  var svg = document.querySelector('.inner svg');
  if (svg) {{
    svgPanZoom(svg, {{
      viewportId: 'diagram-viewport',
      zoomEnabled: true, panEnabled: true, controlIconsEnabled: false,
      fit: true, center: true, zoomScaleSensitivity: 0.5,
      minZoom: 0.1, maxZoom: 50
    }});
  }}
}});
</script>
</body>
</html>'''


# ─── Vega ─────────────────────────────────────────────────────────────────────

def build_vega_html(content: str, name: str) -> str:
    match = re.search(r'```(?:vega-lite|vega)\s*\n(.*?)```', content, re.DOTALL)
    vega_json = match.group(1).strip() if match else '{}'
    esc = vega_json.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{name}</title>
<script src="https://cdn.jsdelivr.net/npm/vega@5/build/vega.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5/build/vega-lite.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6/build/vega-embed.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: 100%; height: 100%; overflow: hidden; background: #1e1e1e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
.wrap {{ width: 100vw; height: 100vh; overflow: hidden; cursor: grab; position: relative; }}
.wrap:active {{ cursor: grabbing; }}
.inner {{ display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; }}
.header {{ position: absolute; top: 0; left: 0; right: 0; z-index: 10; padding: 12px 16px; background: linear-gradient(to bottom, rgba(30,30,30,0.95), transparent); display: flex; align-items: center; gap: 10px; pointer-events: none; }}
h1 {{ color: #e0e0e0; font-size: 16px; font-weight: normal; }}
.note {{ padding: 3px 10px; border-radius: 4px; font-size: 11px; background: rgba(245,158,11,0.9); color: white; }}
#vis {{ width: 90vw; height: 85vh; }}
.hint {{ position: absolute; bottom: 12px; right: 12px; background: rgba(0,0,0,0.55); color: #aaa; font-size: 11px; padding: 5px 10px; border-radius: 4px; pointer-events: none; }}
</style>
</head>
<body>
<div class="wrap" id="wrap">
  <div class="header">
    <h1>{name}</h1>
    <span class="note">🌐 需要网络</span>
  </div>
  <div class="inner">
    <div id="vis"></div>
  </div>
  <div class="hint">滚轮缩放 · 左键拖动平移</div>
</div>
<script>
var spec = JSON.parse('{esc}');
vegaEmbed('#vis', spec, {{ actions: {{export: true, source: false, editor: false}} }}).then(function(result) {{
  var svg = document.querySelector('#vis svg');
  if (svg) {{
    svgPanZoom(svg, {{
      viewportId: 'diagram-viewport',
      zoomEnabled: true, panEnabled: true, controlIconsEnabled: false,
      fit: true, center: true, zoomScaleSensitivity: 0.5,
      minZoom: 0.1, maxZoom: 50
    }});
  }}
}}).catch(console.error);
</script>
</body>
</html>'''


# ─── Infographic ─────────────────────────────────────────────────────────────

def build_infographic_html(content: str, name: str, input_path: str) -> str:
    png_path = input_path.replace('.md', '_截图.png')
    png_name = os.path.basename(png_path)
    if os.path.exists(png_path):
        return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{name}</title>
<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: 100%; height: 100%; overflow: hidden; background: #1e1e1e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
.wrap {{ width: 100vw; height: 100vh; overflow: hidden; cursor: grab; position: relative; }}
.wrap:active {{ cursor: grabbing; }}
.inner {{ display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; }}
.header {{ position: absolute; top: 0; left: 0; right: 0; z-index: 10; padding: 12px 16px; background: linear-gradient(to bottom, rgba(30,30,30,0.95), transparent); display: flex; align-items: center; gap: 10px; pointer-events: none; }}
h1 {{ color: #e0e0e0; font-size: 16px; font-weight: normal; }}
.note {{ padding: 3px 10px; border-radius: 4px; font-size: 11px; background: rgba(99,102,241,0.9); color: white; }}
.inner img {{ max-width: 90vw; max-height: 90vh; border-radius: 6px; box-shadow: 0 4px 20px rgba(0,0,0,0.4); }}
.hint {{ position: absolute; bottom: 12px; right: 12px; background: rgba(0,0,0,0.55); color: #aaa; font-size: 11px; padding: 5px 10px; border-radius: 4px; pointer-events: none; }}
</style>
</head>
<body>
<div class="wrap" id="wrap">
  <div class="header">
    <h1>{name}</h1>
    <span class="note">PNG截图</span>
  </div>
  <div class="inner">
    <img src="{png_name}" alt="{name}"/>
  </div>
  <div class="hint">滚轮缩放 · 左键拖动平移</div>
</div>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  var img = document.querySelector('.inner img');
  if (img) {{
    svgPanZoom(img, {{
      viewportId: 'diagram-viewport',
      zoomEnabled: true, panEnabled: true, controlIconsEnabled: false,
      fit: true, center: true, zoomScaleSensitivity: 0.5,
      minZoom: 0.1, maxZoom: 50
    }});
  }}
}});
</script>
</body>
</html>'''
    else:
        return f'''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>{name}</title></head>
<body style="background:#1e1e1e;padding:20px;color:#e0e0e0;font-family:-apple-system,sans-serif;">
<h1>{name}</h1><p>Infographic PNG截图不存在，请查看同目录截图文件</p></body>
</html>'''


# ─── Canvas ──────────────────────────────────────────────────────────────────

def build_canvas_html(content: str, name: str) -> str:
    match = re.search(r'```canvas\s*\n(.*?)\n```', content, re.DOTALL)
    canvas_json = match.group(1).strip() if match else '{}'
    esc = canvas_json.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{name}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: 100%; height: 100%; overflow: hidden; background: #1e1e1e; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
.wrap {{ width: 100vw; height: 100vh; overflow: hidden; position: relative; }}
.header {{ position: absolute; top: 0; left: 0; right: 0; z-index: 10; padding: 12px 16px; background: linear-gradient(to bottom, rgba(30,30,30,0.95), transparent); display: flex; align-items: center; gap: 10px; }}
h1 {{ color: #e0e0e0; font-size: 16px; font-weight: normal; }}
.note {{ padding: 3px 10px; border-radius: 4px; font-size: 11px; background: rgba(99,102,241,0.9); color: white; }}
pre {{ background: rgba(45,45,45,0.95); border-radius: 8px; padding: 16px; color: #d4d4d4; white-space: pre-wrap; font-size: 12px; margin: 70px 16px 16px; }}
.hint {{ position: absolute; bottom: 12px; right: 12px; background: rgba(0,0,0,0.55); color: #aaa; font-size: 11px; padding: 5px 10px; border-radius: 4px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>{name}</h1>
    <span class="note">Canvas 需 Obsidian 渲染</span>
  </div>
  <pre>{esc}</pre>
  <div class="hint">请在 Obsidian 中查看渲染效果</div>
</div>
</body>
</html>'''


# ─── CLI entry point ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='将含图 .md 转换为可双击的 .html（滚轮缩放+左键拖动）')
    parser.add_argument('--input', '-i', required=True, help='输入 .md 文件路径')
    parser.add_argument('--output', '-o', help='输出 .html 路径（默认同名.html）')
    args = parser.parse_args()
    success = md_to_html(args.input, args.output)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
