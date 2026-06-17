import os
import json
import re
from bs4 import BeautifulSoup

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

project_root = config["project_root"]
cct_folder = config["cct_folder"]
books = config["books"]

raw_output_dir = os.path.join(project_root, "data", "raw")
os.makedirs(raw_output_dir, exist_ok=True)

def clean_cct_markers(text):
    # 移除CCT编号标记
    text = re.sub(r'[Ａ-ＺA-Z]?[\d]+[．\.][\d]+[．\.][\d]+\s*', '', text)
    text = re.sub(r'[Ａ-ＺA-Z]《[^》]*》\s*', '', text)
    text = re.sub(r'[Ａ-ＺA-Z]\s*', '', text)
    text = re.sub(r'[Ａ-ＺA-Z]?[\d]+[．\.][\d]+《[^》]*》\s*', '', text)
    text = re.sub(r'[\d]+[．\.][\d]+[．\.][\d]+\s*', '', text)
    text = re.sub(r'[Ａ-ＺA-Z][\d]+\s*', '', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    return text

def extract_text_from_html(html_path):
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ''.join(chunk for chunk in chunks if chunk)
        text = clean_cct_markers(text)
        return text
    except Exception as e:
        print(f"  解析失败 {os.path.basename(html_path)}: {e}")
        return ""

def process_book(book_name, folder_name):
    folder_path = os.path.join(project_root, cct_folder, folder_name)
    if not os.path.exists(folder_path):
        print(f"警告：文件夹不存在 {folder_path}")
        return
    
    # 创建该书专属子目录
    book_output_dir = os.path.join(raw_output_dir, book_name)
    os.makedirs(book_output_dir, exist_ok=True)
    
    html_files = [f for f in os.listdir(folder_path) if f.endswith('.html') or f.endswith('.htm')]
    html_files.sort()  # 0000, 0001, 0002 ...
    
    if not html_files:
        print(f"警告：{book_name} 文件夹中未找到HTML文件")
        return
    
    print(f"正在处理 {book_name} ... 共 {len(html_files)} 个章节")
    
    for filename in html_files:
        filepath = os.path.join(folder_path, filename)
        chapter_text = extract_text_from_html(filepath)
        if chapter_text:
            # 使用原始数字编号作为文件名
            chap_id = os.path.splitext(filename)[0]  # "0000", "0001" ...
            output_path = os.path.join(book_output_dir, f"{chap_id}.txt")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(chapter_text)
    
    print(f"  {book_name} 提取完成，共 {len(html_files)} 章")
    print(f"  保存至: {book_output_dir}")

print("=" * 40)
print("开始按章节提取古籍文本（数字编号）...")
for book_name, folder_name in books.items():
    process_book(book_name, folder_name)
print("所有书籍提取完成。")