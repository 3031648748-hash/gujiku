import os
import json
import pickle
import re
from collections import defaultdict

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

project_root = config["project_root"]
raw_dir = os.path.join(project_root, "data", "raw")
cache_dir = os.path.join(project_root, "data", "cache")
os.makedirs(cache_dir, exist_ok=True)

N = config.get("ngram_n", 8)
MIN_SENT_LEN = config.get("min_sentence_len", 5)

def segment_sentences(text):
    sentences = re.split(r'([。！？])', text)
    merged = [''.join(i) for i in zip(sentences[0::2], sentences[1::2])]
    if len(sentences) % 2 == 1:
        merged.append(sentences[-1])
    return [s.strip() for s in merged if len(s.strip()) >= MIN_SENT_LEN]

def build_ngram_index(sentences, n=N):
    index = defaultdict(set)
    for sid, sent in enumerate(sentences):
        for i in range(len(sent) - n + 1):
            gram = sent[i:i+n]
            index[gram].add(sid)
    return dict(index)

def process_book(book_name):
    book_dir = os.path.join(raw_dir, book_name)
    if not os.path.exists(book_dir):
        print(f"警告：{book_name} 目录不存在")
        return None
    
    # 获取所有章节文件（数字编号）
    chap_files = [f for f in os.listdir(book_dir) if f.endswith('.txt')]
    chap_files.sort()  # 0000.txt, 0001.txt ...
    
    all_sentences = []
    chapter_boundaries = []  # 记录：(章节编号, 起始句子索引, 结束句子索引)
    
    for chap_file in chap_files:
        chap_id = os.path.splitext(chap_file)[0]  # "0000", "0001" ...
        with open(os.path.join(book_dir, chap_file), 'r', encoding='utf-8') as f:
            text = f.read()
        sents = segment_sentences(text)
        if sents:
            start_idx = len(all_sentences)
            end_idx = start_idx + len(sents) - 1
            chapter_boundaries.append((chap_id, start_idx, end_idx))
            all_sentences.extend(sents)
    
    if not all_sentences:
        print(f"警告：{book_name} 无有效内容")
        return None
    
    index = build_ngram_index(all_sentences, n=N)
    
    cache_path = os.path.join(cache_dir, f"{book_name}.pkl")
    with open(cache_path, 'wb') as f:
        pickle.dump({
            "book_name": book_name,
            "sentences": all_sentences,
            "index": index,
            "n": N,
            "chapter_boundaries": chapter_boundaries  # 存储数字编号 + 句子索引范围
        }, f)
    
    print(f"  {book_name} 完成：{len(all_sentences)} 句，{len(index)} 个N-gram，{len(chapter_boundaries)} 章")
    return index

print("=" * 40)
print("开始构建 N-gram 索引（数字编号章节）...")
books = config["books"]
for book_name in books.keys():
    print(f"正在处理 {book_name}...")
    process_book(book_name)
print("所有书籍索引构建完成。")