import os
import subprocess
import markdown

CSS_STYLE = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fira+Code:wght@400;500&display=swap');

@page {
    size: A4;
    margin: 20mm 15mm 20mm 15mm;
}

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
    line-height: 1.6;
    color: #1f2937;
    background-color: #ffffff;
    margin: 0;
    padding: 0;
}

h1 {
    font-size: 22px;
    font-weight: 700;
    color: #111827;
    border-bottom: 2px solid #3b82f6;
    padding-bottom: 8px;
    margin-top: 0;
    margin-bottom: 16px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

h2 {
    font-size: 16px;
    font-weight: 600;
    color: #1d4ed8;
    background-color: #eff6ff;
    padding: 6px 12px;
    border-left: 4px solid #2563eb;
    margin-top: 24px;
    margin-bottom: 12px;
    border-radius: 0 4px 4px 0;
}

h3 {
    font-size: 14px;
    font-weight: 600;
    color: #1f2937;
    margin-top: 16px;
    margin-bottom: 8px;
}

p, li {
    margin-top: 4px;
    margin-bottom: 6px;
}

ul {
    padding-left: 20px;
    margin-top: 4px;
    margin-bottom: 10px;
}

li {
    margin-bottom: 4px;
}

strong {
    color: #111827;
}

code {
    font-family: 'Fira Code', 'Courier New', Courier, monospace;
    font-size: 12px;
    background-color: #f3f4f6;
    color: #b91c1c;
    padding: 2px 5px;
    border-radius: 4px;
    border: 1px solid #e5e7eb;
}

pre {
    background-color: #0f172a;
    color: #f8fafc;
    padding: 12px 16px;
    border-radius: 6px;
    overflow-x: auto;
    font-family: 'Fira Code', 'Courier New', Courier, monospace;
    font-size: 11.5px;
    line-height: 1.5;
    margin-top: 10px;
    margin-bottom: 12px;
}

pre code {
    background-color: transparent;
    color: inherit;
    padding: 0;
    border: none;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 12px;
    margin-bottom: 16px;
    font-size: 12px;
}

th, td {
    border: 1px solid #d1d5db;
    padding: 8px 10px;
    text-align: left;
}

th {
    background-color: #f3f4f6;
    font-weight: 600;
    color: #111827;
}

tr:nth-child(even) {
    background-color: #f9fafb;
}

hr {
    border: 0;
    height: 1px;
    background: #e5e7eb;
    margin: 20px 0;
}

blockquote {
    background-color: #f8fafc;
    border-left: 4px solid #64748b;
    margin: 12px 0;
    padding: 8px 16px;
    color: #475569;
}
"""

def convert_md_to_pdf(md_filepath, output_pdf_path):
    with open(md_filepath, "r", encoding="utf-8") as f:
        md_content = f.read()

    html_content = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code", "codehilite"]
    )

    full_html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Báo cáo Bài tập về nhà SOA</title>
    <style>
    {CSS_STYLE}
    </style>
</head>
<body>
    {html_content}
</body>
</html>"""

    temp_html_path = md_filepath + ".tmp.html"
    with open(temp_html_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    cmd = [
        chrome_path,
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={output_pdf_path}",
        temp_html_path
    ]

    subprocess.run(cmd, check=True)
    if os.path.exists(temp_html_path):
        os.remove(temp_html_path)

    print(f"Successfully generated PDF: {output_pdf_path}")

if __name__ == "__main__":
    convert_md_to_pdf(
        "/Users/khach/Documents/HOBO/SOA/bai_tap_ve_nha_buoi_1.md",
        "/Users/khach/Documents/HOBO/SOA/BuiDinhCanh_24021392_BTVN_Buoi1.pdf"
    )
    convert_md_to_pdf(
        "/Users/khach/Documents/HOBO/SOA/bai_tap_ve_nha_buoi_1.md",
        "/Users/khach/Documents/HOBO/SOA/bai_tap_ve_nha_buoi_1.pdf"
    )
