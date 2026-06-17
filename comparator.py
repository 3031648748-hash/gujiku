import os
import json
import pickle
import csv
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict

# 设置中文字体，防止图中方框乱码
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC']
plt.rcParams['axes.unicode_minus'] = False

# 加载配置
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

project_root = config["project_root"]
cache_dir = os.path.join(project_root, "data", "cache")
results_dir = os.path.join(project_root, "data", "results")
images_dir = os.path.join(project_root, "images")
os.makedirs(results_dir, exist_ok=True)
os.makedirs(images_dir, exist_ok=True)

# 加载缓存函数
def load_index(book_name):
    cache_path = os.path.join(cache_dir, f"{book_name}.pkl")
    if not os.path.exists(cache_path):
        print(f"错误：{book_name} 的索引文件不存在，请先运行 indexer.py")
        return None
    with open(cache_path, 'rb') as f:
        data = pickle.load(f)
    return data

# 执行比对任务
def compare_books(source_name, target_names, n=8):
    """
    比对源书与多本目标书，计算复用句子数
    """
    print(f"\n比对源书：{source_name}")
    
    source_data = load_index(source_name)
    if source_data is None:
        return []
    
    source_index = source_data["index"]  # ngram -> set(sentence_ids)
    source_sentences = source_data["sentences"]
    
    results = []
    
    for target_name in target_names:
        print(f"  正在比对 -> {target_name}")
        target_data = load_index(target_name)
        if target_data is None:
            continue
        
        target_sentences = target_data["sentences"]
        match_count = 0
        
        # 对目标书的每个句子，检查是否包含源书的任意 N-gram
        for t_sent in target_sentences:
            found = False
            # 滑动窗口检查该句的每个 N-gram
            for i in range(len(t_sent) - n + 1):
                gram = t_sent[i:i+n]
                if gram in source_index:
                    found = True
                    break
            if found:
                match_count += 1
        
        # 计算复用比例（相对于目标书总句数）
        ratio = round(match_count / len(target_sentences) * 100, 2) if target_sentences else 0
        print(f"    发现 {match_count} 个句子复用（占 {target_name} 总句数的 {ratio}%）")
        
        if match_count > 0:
            results.append({
                "source": source_name,
                "target": target_name,
                "weight": match_count
            })
    
    return results

# 执行主程序
if __name__ == "__main__":
    print("=" * 40)
    print("开始执行文本复用比对任务...")
    
    tasks = config.get("tasks", [])
    if not tasks:
        print("警告：config.json 中未定义 tasks 比对任务")
        exit()
    
    all_edges = []
    for task in tasks:
        source = task["source"]
        targets = task["targets"]
        edges = compare_books(source, targets, n=config.get("ngram_n", 8))
        all_edges.extend(edges)
    
    if not all_edges:
        print("\n错误：未检测到任何复用边。尝试降低 config.json 中的 ngram_n 值（例如改为 6）。")
        exit()
    
    # 保存边列表到 CSV
    csv_path = os.path.join(results_dir, "edges.csv")
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["source", "target", "weight"])
        writer.writeheader()
        writer.writerows(all_edges)
    print(f"\n边列表已保存至：{csv_path}")
    
    # --- 绘制网络图 ---
    G = nx.DiGraph()
    for edge in all_edges:
        G.add_edge(edge["source"], edge["target"], weight=edge["weight"])
    
    if len(G.nodes) == 0:
        print("错误：图中没有节点。")
        exit()
    
    plt.figure(figsize=(12, 10))  # 画布稍微放大
    # 增大 k 值拉开距离，scale 放大整体布局
    pos = nx.spring_layout(G, seed=42, k=5, scale=3)
    
    # 绘制节点 - 调小节点尺寸
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=1500)
    nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20, arrowstyle='->')
    nx.draw_networkx_labels(G, pos, font_size=12, font_family='SimHei')
    
    # 绘制权重标签
    edge_labels = {(u, v): str(d['weight']) for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=10)
    
    plt.title("古籍文本复用网络图（有向）", fontsize=16)
    plt.axis('off')
    
    # 保存图片
    img_path = os.path.join(images_dir, "network.png")
    plt.savefig(img_path, dpi=300, bbox_inches='tight')
    print(f"网络图已保存至：{img_path}")
    
    # 显示节点信息
    print("\n网络图节点列表：")
    for node in G.nodes:
        print(f"  - {node}")
    print(f"共 {len(G.nodes)} 个节点，{len(G.edges)} 条边。")
    print("\n全部完成！")