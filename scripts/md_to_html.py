#!/usr/bin/env python3
"""
Markdown 转 HTML 转换器
版本: 3.0.1
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
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1e1e1e; padding: 20px; margin: 0; }}
h1 {{ color: #e0e0e0; margin-bottom: 12px; font-size: 18px; }}
#diagram {{ margin: 0 }}
#diagram svg {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.5); background: white; display: block; }}
#diagram img {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.5); display: block; }}
</style>
</head>
<body>
<h1>{name}</h1>
{note}
<div id="diagram">{svg_content}</div>
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
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1e1e1e; padding: 20px; margin: 0; }}
h1 {{ color: #e0e0e0; margin-bottom: 12px; font-size: 18px; }}
.note {{ background:#3b82f6;color:white;padding:6px 14px;border-radius:4px;margin-bottom:12px;display:inline-block;font-size:12px; }}
#diagram {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 4px 16px rgba(0,0,0,0.5); }}
</style>
</head>
<body>
<h1>{name}</h1>
<div class="note">🌐 需要网络连接渲染 Mermaid 图</div>
<div class="mermaid">{escaped}</div>
<script>mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});</script>
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
<style>
body {{ background: #f0f4f8; margin: 0; padding: 20px; display: flex; justify-content: center; }}
{style_content}
</style>
</head>
<body>
{html_block}
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
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1e1e1e; padding: 20px; margin: 0; }}
h1 {{ color: #e0e0e0; margin-bottom: 12px; font-size: 18px; }}
.note {{ background:#f59e0b;color:white;padding:6px 14px;border-radius:4px;margin-bottom:12px;display:inline-block;font-size:12px; }}
#vis {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 4px 16px rgba(0,0,0,0.5); }}
</style>
</head>
<body>
<h1>{name}</h1>
<div class="note">🌐 需要网络连接渲染 Vega 图表</div>
<div id="vis"></div>
<script>
var spec = JSON.parse('{escaped}');
vegaEmbed('#vis', spec, {{ actions: {{export: true, source: false, editor: false}} }}).then(function(){{}}).catch(console.error);
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
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1e1e1e; padding: 20px; margin: 0; display: flex; justify-content: center; }}
img {{ max-width: 900px; width: 100%; height: auto; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.5); }}
</style>
</head>
<body>
<img src="{png_name}" alt="{name}">
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
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1e1e1e; padding: 20px; margin: 0; }}
h1 {{ color: #e0e0e0; margin-bottom: 12px; font-size: 18px; }}
.note {{ background:#6366f1;color:white;padding:6px 14px;border-radius:4px;margin-bottom:12px;display:inline-block;font-size:12px; }}
pre {{ background: #2d2d2d; border-radius: 8px; padding: 16px; color: #d4d4d4; white-space: pre-wrap; font-size: 12px; }}
</style>
</head>
<body>
<h1>{name}</h1>
<div class="note">Canvas 需 Obsidian 渲染，JSON数据如下：</div>
<pre>{escaped}</pre>
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
