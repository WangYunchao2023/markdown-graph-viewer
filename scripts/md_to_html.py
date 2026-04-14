#!/usr/bin/env python3
"""
Markdown 转 HTML 转换器
版本: 3.0.0
将含 PlantUML / HTML 代码的 .md 文件转换为可直接双击打开的 .html
支持：PlantUML / HTML / Mermaid / Vega-Lite / 纯文本图（PNG引用）
"""

import argparse
import re
import os
import sys

def md_to_html(input_path: str, output_path: str = None) -> bool:
    """将 .md 文件转换为可双击打开的 HTML"""
    
    if output_path is None:
        output_path = input_path.rstrip('.md') + '.html'
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"读取文件失败: {e}", file=sys.stderr)
        return False
    
    # 判断图表类型
    if '```plantuml' in content or '@startuml' in content:
        chart_type = 'plantuml'
    elif '```mermaid' in content:
        chart_type = 'mermaid'
    elif '<div' in content and 'style=' in content:
        chart_type = 'html'
    elif '```vega' in content or '```vega-lite' in content:
        chart_type = 'vega'
    elif '```infographic' in content:
        chart_type = 'infographic'
    elif '```canvas' in content or '"nodes":' in content:
        chart_type = 'canvas'
    else:
        chart_type = 'unknown'
    
    name = os.path.basename(input_path).replace('.md', '')
    
    if chart_type == 'plantuml':
        html = build_plantuml_html(content, name)
    elif chart_type == 'mermaid':
        html = build_mermaid_html(content, name)
    elif chart_type == 'html':
        html = build_pure_html(content, name)
    elif chart_type == 'vega':
        html = build_vega_html(content, name)
    elif chart_type == 'infographic':
        html = build_infographic_html(content, name, input_path)
    elif chart_type == 'canvas':
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


def plantuml_encode(s):
    """PlantUML encoder for URL"""
    import base64
    import zlib
    data = zlib.compress(bytes(s, 'utf-8'))[2:-4]
    return base64.b64encode(data).decode('utf-8')


def build_plantuml_html(content: str, name: str) -> str:
    """PlantUML .md → 可双击HTML（本地 PlantUML SVG渲染，离线可用）"""
    import subprocess
    match = re.search(r'```plantuml\s*\n(.*?)```', content, re.DOTALL)
    if not match:
        match = re.search(r'```puml\s*\n(.*?)```', content, re.DOTALL)
    puml_code = match.group(1).strip() if match else ''
    svg_content = ''
    fallback_note = '<div style="background:#f59e0b;color:white;padding:8px 16px;border-radius:4px;margin-bottom:16px;display:inline-block;font-size:12px;">🌐 PlantUML本地渲染（离线可用）</div>'
    if puml_code:
        try:
            result = subprocess.run(
                ['plantuml', '-tsvg', '-p'],
                input=puml_code.encode('utf-8'),
                capture_output=True, timeout=30
            )
            if result.returncode == 0 and result.stdout:
                svg_content = result.stdout.decode('utf-8')
                fallback_note = '<div style="background:#22c55e;color:white;padding:8px 16px;border-radius:4px;margin-bottom:16px;display:inline-block;font-size:12px;">✅ 本地SVG渲染成功（无需网络）</div>'
            else:
                err = result.stderr.decode('utf-8')[:80] if result.stderr else 'unknown'
                fallback_note = f'<div style="background:#f97316;color:white;padding:8px 16px;border-radius:4px;margin-bottom:16px;display:inline-block;font-size:12px;">⚠️ 本地渲染失败：{err}，请检查PlantUML安装</div>'
                encoded = plantuml_encode(puml_code)
                svg_content = f'<img src="http://www.plantuml.com/plantuml/svg/{encoded}" style="max-width:100%;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.3);" onerror="this.parent.innerHTML=\'<p style=color:#f48771;>⚠️ 在线渲染也失败</p>\';this.remove()">'
        except FileNotFoundError:
            fallback_note = '<div style="background:#ef4444;color:white;padding:8px 16px;border-radius:4px;margin-bottom:16px;display:inline-block;font-size:12px;">⚠️ PlantUML未安装，改为在线渲染（需网络）</div>'
            encoded = plantuml_encode(puml_code)
            svg_content = f'<img src="http://www.plantuml.com/plantuml/svg/{encoded}" style="max-width:100%;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.3);" onerror="this.parent.innerHTML=\'<p style=color:#f48771;>⚠️ 渲染失败，请安装PlantUML</p>\';this.remove()">'
        except Exception as e:
            fallback_note = f'<div style="background:#f97316;color:white;padding:8px 16px;border-radius:4px;margin-bottom:16px;display:inline-block;font-size:12px;">⚠️ 渲染异常：{str(e)[:60]}，改为在线（需网络）</div>'
            encoded = plantuml_encode(puml_code)
            svg_content = f'<img src="http://www.plantuml.com/plantuml/svg/{encoded}" style="max-width:100%;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.3);">'
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{name}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1e1e1e; color: #d4d4d4; padding: 20px; margin: 0; }}
pre {{ background: #2d2d2d; border-radius: 8px; padding: 16px; overflow-x: auto; font-size: 13px; line-height: 1.6; margin-top: 20px; }}
h1 {{ color: #e0e0e0; margin-bottom: 20px; }}
h2 {{ color: #e0e0e0; margin: 20px 0 10px 0; font-size: 16px; }}
#diagram {{ margin-top: 20px; }}
#diagram svg {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); background: white; }}
#diagram img {{ max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }}
</style>
</head>
<body>
<h1>{name}</h1>
{fallback_note}
<h2>PlantUML 源码</h2>
<pre>{puml_code}</pre>
<h2>渲染结果</h2>
<div id="diagram">{svg_content}</div>
</body>
</html>'''


def build_mermaid_html(content: str, name: str) -> str:
    """Mermaid .md → 可双击HTML"""
    
    match = re.search(r'```mermaid\s*\n(.*?)```', content, re.DOTALL)
    mermaid_code = match.group(1).strip() if match else ''
    
    # HTML转义
    escaped = mermaid_code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{name}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1e1e1e; color: #d4d4d4; padding: 20px; margin: 0; }}
pre {{ background: #2d2d2d; border-radius: 8px; padding: 16px; overflow-x: auto; font-size: 13px; }}
#diagram {{ margin-top: 20px; background: white; border-radius: 8px; padding: 20px; }}
.offline {{ background: #569cd6; color: white; padding: 8px 16px; border-radius: 4px; font-size: 12px; margin-bottom: 16px; display: inline-block; }}
</style>
</head>
<body>
<h1 style="color:#e0e0e0; margin-bottom:20px;">{name}</h1>
<pre id="code" style="display:none;">{escaped}</pre>
<div class="offline">🌐 需要网络连接才能渲染 Mermaid 图</div>
<div id="diagram" class="mermaid"></div>
<script>
mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
var code = document.getElementById('code').textContent;
document.getElementById('diagram').textContent = code;
mermaid.run({{ nodes: ['#diagram'] }});
</script>
</body>
</html>'''


def build_pure_html(content: str, name: str) -> str:
    """纯HTML .md → 独立HTML文件"""
    
    # 提取第一个<div...开始的内容块
    match = re.search(r'(<div style="width:.*)', content, re.DOTALL)
    if not match:
        return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>{name}</title></head>
<body><pre>{content}</pre></body></html>'''
    
    html_block = match.group(1)
    # 找到匹配的关闭标签
    depth = html_block.count('<div') - 1
    end_pos = 0
    search_from = 0
    for _ in range(depth):
        idx = html_block.find('</div>', search_from)
        if idx == -1:
            break
        end_pos = idx + 6
        search_from = idx + 6
    
    if end_pos > 0:
        html_block = html_block[:end_pos]
    
    # 提取style标签内容
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


def build_vega_html(content: str, name: str) -> str:
    """Vega/Vega-Lite .md → 独立HTML"""
    
    match = re.search(r'```(?:vega-lite|vega)\s*\n(.*?)```', content, re.DOTALL)
    vega_json = match.group(1).strip() if match else '{}'
    
    escaped = vega_json.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
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
#vis {{ background: white; border-radius: 8px; padding: 20px; margin-top: 20px; }}
.offline {{ background: #f59e0b; color: white; padding: 8px 16px; border-radius: 4px; font-size: 12px; margin-bottom: 16px; display: inline-block; }}
</style>
</head>
<body>
<h1 style="color:#e0e0e0; margin-bottom:20px;">{name}</h1>
<div class="offline">🌐 需要网络连接才能渲染 Vega 图表</div>
<div id="vis"></div>
<script>
var spec = JSON.parse('{escaped}');
vegaEmbed('#vis', spec, {{ actions: {{export: true, source: false, editor: false}} }}).then(function(result) {{}}).catch(console.error);
</script>
</body>
</html>'''


def build_infographic_html(content: str, name: str, input_path: str) -> str:
    """Infographic .md → HTML（嵌入PNG截图）"""
    
    # 查找同名的PNG截图
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
img {{ max-width: 900px; width: 100%; height: auto; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.4); }}
</style>
</head>
<body>
<img src="{png_name}" alt="{name}">
</body>
</html>'''
    else:
        # 没有PNG时显示代码
        return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{name}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1e1e1e; color: #d4d4d4; padding: 20px; }}
pre {{ background: #2d2d2d; border-radius: 8px; padding: 16px; overflow-x: auto; }}
</style>
</head>
<body>
<h1>{name}</h1>
<pre>注意：Infographic 需要渲染截图，请查看同目录的 PNG 文件</pre>
</body>
</html>'''


def build_canvas_html(content: str, name: str) -> str:
    """Canvas JSON → 简单HTML展示"""
    
    match = re.search(r'```canvas\s*\n(.*?)\n```', content, re.DOTALL)
    canvas_json = match.group(1).strip() if match else '{}'
    
    escaped = canvas_json.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    
    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{name}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1e1e1e; color: #d4d4d4; padding: 20px; }}
#canvas-container {{ background: white; border-radius: 8px; padding: 20px; margin-top: 20px; min-height: 400px; }}
</style>
</head>
<body>
<h1 style="color:#e0e0e0; margin-bottom:20px;">{name}</h1>
<div id="canvas-container">
  <p style="color:#666;">Canvas 图：需要 Obsidian Canvas 渲染，JSON数据如下：</p>
  <pre>{escaped}</pre>
</div>
</body>
</html>'''


def main():
    parser = argparse.ArgumentParser(description='将 .md 文件（含PlantUML/HTML/Mermaid图表）转换为可直接双击打开的 .html')
    parser.add_argument('--input', '-i', required=True, help='输入 .md 文件路径')
    parser.add_argument('--output', '-o', help='输出 .html 文件路径（默认：输入名.html）')
    args = parser.parse_args()
    
    success = md_to_html(args.input, args.output)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
