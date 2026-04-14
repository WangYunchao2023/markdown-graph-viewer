#!/usr/bin/env python3
"""
Markdown 转 HTML 转换器
版本: 3.0.2
将含 PlantUML / HTML 代码的 .md 文件转换为可直接双击打开的 .html
支持：PlantUML / HTML / Mermaid / Vega-Lite / Infographic / Canvas
"""

import argparse
import re
import os
import sys
import subprocess


def md_to_html(input_path: str, output_path: str = None) -> bool:
    """将 .md 文件转换为可双击打开的 HTML（只显示渲染图，无源码）"""
    if output_path is None:
        output_path = input_path.rstrip('.md') + '.html'
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"读取文件失败: {e}", file=sys.stderr)
        return False

    if '```plantuml' in content or '@startuml' in content:
        html = build_plantuml_html(content, os.path.basename(input_path).replace('.md', ''))
    elif '```mermaid' in content:
        html = build_mermaid_html(content, os.path.basename(input_path).replace('.md', ''))
    elif '<div' in content and 'style=' in content:
        html = build_pure_html(content, os.path.basename(input_path).replace('.md', ''))
    elif '```vega' in content or '```vega-lite' in content:
        html = build_vega_html(content, os.path.basename(input_path).replace('.md', ''))
    elif '```infographic' in content:
        html = build_infographic_html(content, os.path.basename(input_path).replace('.md', ''), input_path)
    elif '```canvas' in content or '"nodes":' in content:
        html = build_canvas_html(content, os.path.basename(input_path).replace('.md', ''))
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


# ─── PlantUML ───────────────────────────────────────────────────────────────────

def plantuml_encode(s):
    """PlantUML URL encoder"""
    import base64, zlib
    return base64.b64encode(zlib.compress(bytes(s, 'utf-8'))[2:-4]).decode('utf-8')


def build_plantuml_html(content: str, name: str) -> str:
    """PlantUML .md → 只显示渲染图（无源码）"""
    match = re.search(r'```plantuml\s*\n(.*?)```', content, re.DOTALL)
    if not match:
        match = re.search(r'```puml\s*\n(.*?)```', content, re.DOTALL)
    puml_code = match.group(1).strip() if match else ''
    svg_content = ''
    note = '<div style="background:#22c55e;color:white;padding:6px 14px;border-radius:4px;margin-bottom:12px;display:inline-block;font-size:12px;">✅ SVG渲染成功</div>'
    if puml_code:
        try:
            result = subprocess.run(
                ['plantuml', '-tsvg', '-p'],
                input=puml_code.encode('utf-8'),
                capture_output=True, timeout=30
            )
            if result.returncode == 0 and result.stdout:
                svg_content = result.stdout.decode('utf-8')
            else:
                err = result.stderr.decode('utf-8')[:60] if result.stderr else 'unknown'
                note = f'<div style="background:#f97316;color:white;padding:6px 14px;border-radius:4px;margin-bottom:12px;display:inline-block;font-size:12px;">⚠️ 本地失败：{err}</div>'
                encoded = plantuml_encode(puml_code)
                svg_content = f'<img src="http://www.plantuml.com/plantuml/svg/{encoded}" style="max-width:100%;border-radius:8px;" onerror="this.parent.innerHTML=\'<p>⚠️ 在线渲染失败</p>\';this.remove()">'
        except FileNotFoundError:
            note = '<div style="background:#ef4444;color:white;padding:6px 14px;border-radius:4px;margin-bottom:12px;display:inline-block;font-size:12px;">⚠️ PlantUML未安装，改为在线渲染</div>'
            encoded = plantuml_encode(puml_code)
            svg_content = f'<img src="http://www.plantuml.com/plantuml/svg/{encoded}" style="max-width:100%;border-radius:8px;">'
        except Exception as e:
            note = f'<div style="background:#f97316;color:white;padding:6px 14px;border-radius:4px;margin-bottom:12px;display:inline-block;font-size:12px;">⚠️ 异常：{str(e)[:60]}</div>'
            encoded = plantuml_encode(puml_code)
            svg_content = f'<img src="http://www.plantuml.com/plantuml/svg/{encoded}" style="max-width:100%;border-radius:8px;">'
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{name}</title>
<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #222; padding: 0; margin: 0; overflow: hidden; height: 100vh; }}
h1 {{ color: #e0e0e0; margin: 12px 16px; font-size: 16px; position: absolute; top: 0; left: 0; z-index: 10; }}
.note {{ background: rgba(34,197,94,0.9); color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px; margin-left: 16px; }}
#diagram {{ width: 100vw; height: 100vh; cursor: grab; }}
#diagram:active {{ cursor: grabbing; }}
#diagram svg {{ width: 100% !important; height: 100% !important; border-radius: 0; box-shadow: none; background: white; display: block; }}
#diagram img {{ width: 100%; height: 100%; object-fit: contain; border-radius: 0; box-shadow: none; }}
.hint {{ position: fixed; bottom: 12px; right: 12px; background: rgba(0,0,0,0.6); color: #aaa; font-size: 11px; padding: 6px 10px; border-radius: 4px; z-index: 10; }}
</style>
</head>
<body>
<h1>{name} <span class="note">{note}</span></h1>
<div id="diagram">{svg_content}</div>
<div class="hint">滚轮缩放 · 左键拖动平移</div>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  var el = document.querySelector('#diagram svg');
  if (el) {{
    svgPanZoom(el, {{
      zoomEnabled: true, panEnabled: true, controlIconsEnabled: false,
      fit: true, center: true, zoomScaleSensitivity: 0.4,
      minZoom: 0.1, maxZoom: 20
    }});
  }}
}});
</script>
</body>
</html>'''


# ─── Mermaid ────────────────────────────────────────────────────────────────────

def build_mermaid_html(content: str, name: str) -> str:
    """Mermaid .md → 只显示渲染图（无源码）"""
    match = re.search(r'```mermaid\s*\n(.*?)```', content, re.DOTALL)
    mermaid_code = match.group(1).strip() if match else ''
    escaped = mermaid_code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{name}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #222; padding: 0; margin: 0; overflow: hidden; height: 100vh; }}
h1 {{ color: #e0e0e0; margin: 12px 16px; font-size: 16px; position: absolute; top: 0; left: 0; z-index: 10; }}
.note {{ background: rgba(59,130,246,0.9); color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px; margin-left: 10px; }}
#diagram {{ width: 100vw; height: 100vh; cursor: grab; }}
#diagram:active {{ cursor: grabbing; }}
.mermaid {{ width: 100% !important; height: 100% !important; }}
.mermaid svg {{ width: 100% !important; height: 100% !important; }}
.hint {{ position: fixed; bottom: 12px; right: 12px; background: rgba(0,0,0,0.6); color: #aaa; font-size: 11px; padding: 6px 10px; border-radius: 4px; z-index: 10; }}
</style>
</head>
<body>
<h1>{name} <span class="note">🌐 需要网络</span></h1>
<div id="diagram"><div class="mermaid">{escaped}</div></div>
<div class="hint">滚轮缩放 · 左键拖动平移</div>
<script>
mermaid.initialize({{ startOnLoad: false, theme: 'dark' }});
mermaid.run().then(function() {{
  var el = document.querySelector('#diagram .mermaid svg');
  if (el) {{
    svgPanZoom(el, {{ zoomEnabled: true, panEnabled: true, controlIconsEnabled: false, fit: true, center: true, zoomScaleSensitivity: 0.4, minZoom: 0.05, maxZoom: 50 }});
  }}
}});
</script>
</body>
</html>'''


# ─── 纯 HTML ──────────────────────────────────────────────────────────────────

def build_pure_html(content: str, name: str) -> str:
    """HTML .md → 独立HTML文件"""
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
body {{ background: #f0f4f8; margin: 0; padding: 0; overflow: hidden; height: 100vh; display: flex; align-items: center; justify-content: center; }}
{style_content}
.svg-container {{ width: 100vw; height: 100vh; cursor: grab; overflow: hidden; }}
.svg-container:active {{ cursor: grabbing; }}
.hint {{ position: fixed; bottom: 12px; right: 12px; background: rgba(0,0,0,0.6); color: #aaa; font-size: 11px; padding: 6px 10px; border-radius: 4px; }}
</style>
</head>
<body>
<div class="svg-container" id="container">{html_block}</div>
<div class="hint">滚轮缩放 · 左键拖动平移</div>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  var el = document.querySelector('.svg-container svg');
  if (el) {{
    svgPanZoom(el, {{ zoomEnabled: true, panEnabled: true, controlIconsEnabled: false, fit: true, center: true, zoomScaleSensitivity: 0.4, minZoom: 0.1, maxZoom: 20 }});
  }}
}});
</script>
</body>
</html>'''


# ─── Vega ─────────────────────────────────────────────────────────────────────

def build_vega_html(content: str, name: str) -> str:
    """Vega/Vega-Lite .md → 独立HTML"""
    match = re.search(r'```(?:vega-lite|vega)\s*\n(.*?)```', content, re.DOTALL)
    vega_json = match.group(1).strip() if match else '{}'
    escaped = vega_json.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{name}</title>
<script src="https://cdn.jsdelivr.net/npm/vega@5/build/vega.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5/build/vega-lite.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6/build/vega-embed.min.js"></script>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #222; padding: 0; margin: 0; overflow: hidden; height: 100vh; }}
h1 {{ color: #e0e0e0; margin: 12px 16px; font-size: 16px; position: absolute; top: 0; left: 0; z-index: 10; }}
.note {{ background: rgba(245,158,11,0.9); color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px; margin-left: 10px; }}
#vis {{ width: 100vw; height: 100vh; cursor: grab; }}
#vis:active {{ cursor: grabbing; }}
.hint {{ position: fixed; bottom: 12px; right: 12px; background: rgba(0,0,0,0.6); color: #aaa; font-size: 11px; padding: 6px 10px; border-radius: 4px; z-index: 10; }}
</style>
</head>
<body>
<h1>{name} <span class="note">🌐 需要网络</span></h1>
<div id="vis"></div>
<div class="hint">滚轮缩放 · 左键拖动平移</div>
<script>
var spec = JSON.parse('{escaped}');
vegaEmbed('#vis', spec, {{ actions: {{export: true, source: false, editor: false}}, scaleFactor: 2 }}).then(function(result) {{
  var el = result.spec && document.querySelector('#vis svg');
  if (el) {{
    svgPanZoom(el, {{ zoomEnabled: true, panEnabled: true, controlIconsEnabled: false, fit: true, center: true, zoomScaleSensitivity: 0.4, minZoom: 0.1, maxZoom: 20 }});
  }}
}}).catch(console.error);
</script>
</body>
</html>'''


# ─── Infographic ─────────────────────────────────────────────────────────────

def build_infographic_html(content: str, name: str, input_path: str) -> str:
    """Infographic .md → HTML（嵌入PNG截图）"""
    png_path = input_path.replace('.md', '_截图.png')
    png_name = os.path.basename(png_path)
    if os.path.exists(png_path):
        return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{name}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #222; padding: 0; margin: 0; overflow: hidden; height: 100vh; display: flex; align-items: center; justify-content: center; }}
img {{ max-width: 95vw; max-height: 95vh; object-fit: contain; border-radius: 8px; box-shadow: 0 8px 32px rgba(0,0,0,0.6); }}
.hint {{ position: fixed; bottom: 12px; right: 12px; background: rgba(0,0,0,0.6); color: #aaa; font-size: 11px; padding: 6px 10px; border-radius: 4px; }}
</style>
</head>
<body>
<img src="{png_name}" alt="{name}">
<div class="hint">滚轮缩放 · 左键拖动平移</div>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  var el = document.querySelector('img');
  if (el) {{
    svgPanZoom(el, {{ zoomEnabled: true, panEnabled: true, controlIconsEnabled: false, fit: true, center: true, zoomScaleSensitivity: 0.4, minZoom: 0.1, maxZoom: 20 }});
  }}
}});
</script>
</body>
</html>'''
    else:
        return f'''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>{name}</title></head>
<body><h1>{name}</h1><p>Infographic 需要截图，请查看同目录的 PNG 文件</p></body>
</html>'''


# ─── Canvas ──────────────────────────────────────────────────────────────────

def build_canvas_html(content: str, name: str) -> str:
    """Canvas JSON → HTML"""
    match = re.search(r'```canvas\s*\n(.*?)\n```', content, re.DOTALL)
    canvas_json = match.group(1).strip() if match else '{}'
    escaped = canvas_json.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{name}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #222; padding: 0; margin: 0; overflow: hidden; height: 100vh; }}
h1 {{ color: #e0e0e0; margin: 12px 16px; font-size: 16px; position: absolute; top: 0; left: 0; z-index: 10; }}
.note {{ background: rgba(99,102,241,0.9); color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px; margin-left: 10px; }}
pre {{ background: rgba(45,45,45,0.95); border-radius: 8px; padding: 16px; color: #d4d4d4; white-space: pre-wrap; font-size: 12px; margin: 60px 16px 16px; }}
.hint {{ position: fixed; bottom: 12px; right: 12px; background: rgba(0,0,0,0.6); color: #aaa; font-size: 11px; padding: 6px 10px; border-radius: 4px; }}
</style>
</head>
<body>
<h1>{name} <span class="note">Canvas 需 Obsidian 渲染</span></h1>
<pre>{escaped}</pre>
<div class="hint">仅展示 JSON 数据，请在 Obsidian 中查看渲染效果</div>
</body>
</html>'''


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='将 .md（含PlantUML/HTML/Mermaid图表）转换为只显示图的 .html')
    parser.add_argument('--input', '-i', required=True, help='输入 .md 文件路径')
    parser.add_argument('--output', '-o', help='输出 .html 文件路径（默认：输入名.html）')
    args = parser.parse_args()
    success = md_to_html(args.input, args.output)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
