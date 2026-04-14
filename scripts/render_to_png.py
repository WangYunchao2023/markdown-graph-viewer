#!/usr/bin/env python3
"""
飞书兼容图表渲染脚本
版本: 3.0.0
将 PlantUML / HTML 图表渲染为 PNG 截图
"""

import subprocess
import sys
import os
import tempfile
import argparse

def render_plantuml(puml_code: str, output_path: str) -> bool:
    """用 PlantUML 渲染 PlantUML 代码为 PNG"""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.puml', delete=False) as f:
            f.write(puml_code)
            temp_file = f.name
        
        result = subprocess.run(
            ['plantuml', '-Tpng', '-o', os.path.dirname(output_path), temp_file],
            capture_output=True, text=True, timeout=60
        )
        os.unlink(temp_file)
        
        # PlantUML 输出文件名与输入文件同名
        expected_png = temp_file.replace('.puml', '.png')
        if os.path.exists(expected_png) and expected_png != output_path:
            os.rename(expected_png, output_path)
        
        if result.returncode == 0 and os.path.exists(output_path):
            return True
        return False
    except Exception as e:
        print(f"PlantUML 渲染失败: {e}", file=sys.stderr)
        return False

def render_html_to_png(html_code: str, output_path: str, width: int = 1200) -> bool:
    """用 Playwright + Chrome 把 HTML 渲染为 PNG"""
    try:
        from playwright.sync_api import sync_playwright
        import base64

        with sync_playwright() as p:
            browser = p.chromium.launch(
                args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
            )
            page = browser.new_page(viewport={'width': width, 'height': 800})
            page.set_content(html_code, wait_until='networkidle', timeout=30000)
            page.screenshot(path=output_path, full_page=True, type='png')
            browser.close()
            return True
    except Exception as e:
        print(f"HTML 渲染失败: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description='图表渲染为PNG')
    parser.add_argument('--type', choices=['plantuml', 'html'], required=True, help='图表类型')
    parser.add_argument('--input', required=True, help='输入文件路径')
    parser.add_argument('--output', required=True, help='输出PNG路径')
    args = parser.parse_args()

    if args.type == 'plantuml':
        with open(args.input, 'r') as f:
            code = f.read()
        success = render_plantuml(code, args.output)
    elif args.type == 'html':
        with open(args.input, 'r') as f:
            code = f.read()
        success = render_html_to_png(code, args.output)

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
