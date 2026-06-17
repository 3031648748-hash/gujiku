import streamlit as st
import pickle
import os
import json
import re
import networkx as nx
import matplotlib.pyplot as plt

st.set_page_config(page_title="古籍文本复用比对平台", layout="wide")

# ========== CSS（已修复 st.code 黑底问题） ==========
st.markdown("""
<style>
    .stApp, .stApp * { color: #3d2e1e !important; }
    .stApp { background-color: #f5f0e8 !important; }
    .main > div { background-color: #f9f5ec !important; padding: 20px 30px; border-radius: 12px; }
    .stSidebar { background-color: #ede7dc !important; border-right: 2px solid #d6cdbc; }
    .stSidebar * { color: #3d2e1e !important; }
    .stSelectbox > div > div { background-color: #f5f0e8 !important; color: #3d2e1e !important; }
    h1, h2, h3, h4 { color: #4a3729 !important; font-family: "Noto Serif SC", "STKaiti", serif; }
    .guwen-box {
        height: 500px;
        overflow-y: scroll;
        border: 1px solid #d6cdbc;
        border-radius: 8px;
        padding: 18px 22px;
        background-color: #fcf9f2;
        font-size: 15px;
        line-height: 2.2;
        color: #3d2e1e !important;
        font-family: "Noto Serif SC", "SimSun", serif;
        scroll-behavior: smooth;
    }
    .guwen-box * { color: #3d2e1e !important; }
    .highlight { background-color: #f7e5b0 !important; padding: 2px 4px; border-radius: 3px; border-bottom: 2px solid #d4b68a; }
    .jump-arrow {
        color: #8B4513 !important;
        text-decoration: none !important;
        font-weight: bold;
        margin-left: 6px;
        font-size: 18px;
        cursor: pointer;
        border: 1px solid #d4b68a;
        border-radius: 12px;
        padding: 0 6px;
        background-color: #ede7dc;
        transition: all 0.2s;
    }
    .jump-arrow:hover { background-color: #d4b68a; color: #ffffff !important; border-color: #8B4513; }
    .section-marker { display: block; font-size: 14px; font-weight: bold; color: #7a5d42 !important; margin: 12px 0 6px 0; padding: 4px 10px; border-left: 4px solid #b8a085; background-color: #eee6d8; border-radius: 0 4px 4px 0; font-family: "STKaiti", serif; }
    .metric-box { background-color: #ede7dc; padding: 6px 16px; border-radius: 20px; color: #4a3729 !important; font-weight: bold; display: inline-block; }
    
    .match-item {
        padding: 8px 14px;
        margin: 4px 0;
        border-left: 3px solid #d4b68a;
        background-color: #faf6ed;
        border-radius: 0 6px 6px 0;
        font-size: 14px;
        line-height: 1.8;
    }
    .match-item:hover { background-color: #ede7dc; }
    .match-item .sim-tag {
        display: inline-block;
        background-color: #d4b68a;
        color: white !important;
        padding: 0 10px;
        border-radius: 12px;
        font-size: 12px;
        margin-right: 10px;
        font-weight: bold;
    }
    .match-item .chap-tag {
        display: inline-block;
        background-color: #ddd0be;
        color: #3d2e1e !important;
        padding: 0 8px;
        border-radius: 10px;
        font-size: 11px;
        margin-right: 8px;
    }
    .match-item .jump-link {
        margin-left: 12px;
        color: #8B4513 !important;
        text-decoration: none;
        border: 1px solid #d4b68a;
        border-radius: 12px;
        padding: 0 8px;
        font-size: 13px;
        background: #ede7dc;
        cursor: pointer;
    }
    .match-item .jump-link:hover { background: #d4b68a; color: white !important; }
    
    .stButton button {
        background-color: #d6cdbc !important;
        color: #3d2e1e !important;
        border: none !important;
        font-family: "STKaiti", serif !important;
    }
    .stButton button:hover {
        background-color: #c4b5a0 !important;
        color: #3d2e1e !important;
    }
    
    /* ====== 新增：修复 st.code 代码块为白色背景 ====== */
    .stCodeBlock {
        background-color: #f5f0e8 !important;
        border: 1px solid #d6cdbc !important;
        border-radius: 6px !important;
        padding: 12px !important;
    }
    .stCodeBlock pre {
        background-color: #fcf9f2 !important;
        color: #3d2e1e !important;
        font-family: "Consolas", "Noto Serif SC", monospace !important;
    }
    .stCodeBlock code {
        background-color: #fcf9f2 !important;
        color: #3d2e1e !important;
    }
    .stSidebar .stCodeBlock {
        background-color: #ede7dc !important;
    }
    .stSidebar .stCodeBlock pre,
    .stSidebar .stCodeBlock code {
        background-color: #f5f0e8 !important;
        color: #3d2e1e !important;
    }
    code {
        background-color: #f5f0e8 !important;
        color: #3d2e1e !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        border: 1px solid #e0d6c8 !important;
    }
    pre {
        background-color: #fcf9f2 !important;
        color: #3d2e1e !important;
        border: 1px solid #d6cdbc !important;
        border-radius: 6px !important;
        padding: 12px !important;
    }
</style>
""", unsafe_allow_html=True)

# ========== 配置加载 ==========
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)
project_root = config["project_root"]
cache_dir = os.path.join(project_root, "data", "cache")

def get_indexed_books():
    return [f.replace(".pkl", "") for f in os.listdir(cache_dir) if f.endswith(".pkl")]

@st.cache_data
def load_book_data(book_name):
    path = os.path.join(cache_dir, f"{book_name}.pkl")
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data

def split_sentences(text):
    sents = re.split(r'([。！？])', text)
    merged = [''.join(i) for i in zip(sents[0::2], sents[1::2])]
    if len(sents) % 2 == 1:
        merged.append(sents[-1])
    return [s.strip() for s in merged if len(s.strip()) > 2]

def find_matching_pairs(source_sents, source_idx, target_sents, target_idx, n, threshold):
    matches = []
    for t_idx, t_sent in enumerate(target_sents):
        matched_ngrams = 0
        total = max(1, len(t_sent) - n + 1)
        for i in range(len(t_sent) - n + 1):
            if t_sent[i:i+n] in source_idx:
                matched_ngrams += 1
        if total > 0:
            sim = matched_ngrams / total * 100
            if sim >= threshold and matched_ngrams > 0:
                src_set = set()
                for i in range(len(t_sent) - n + 1):
                    gram = t_sent[i:i+n]
                    if gram in source_idx:
                        for sid in source_idx[gram]:
                            src_set.add(sid)
                if src_set:
                    matches.append((list(src_set)[0], t_idx, round(sim, 1)))
    return matches

def build_chapter_html(title, sentences, highlight_indices, match_map, side="left"):
    parts = []
    parts.append(f'<span class="section-marker">章节 {title}</span>')
    for i, sent in enumerate(sentences):
        if i in highlight_indices and match_map and i in match_map:
            match_id = match_map[i]
            if side == "left":
                parts.append(
                    f'<span class="highlight" id="src_{match_id}">'
                    f'{sent}'
                    f' <a href="#tgt_{match_id}" class="jump-arrow" title="跳转到右侧对应句">↘</a>'
                    f'</span>'
                )
            else:
                parts.append(f'<span class="highlight" id="tgt_{match_id}">{sent}</span>')
        else:
            parts.append(sent)
    return ''.join(parts)

# ========== Session State 初始化 ==========
if 'pair_idx' not in st.session_state:
    st.session_state.pair_idx = 0
if 'display_limit' not in st.session_state:
    st.session_state.display_limit = 30
if 'jump_mid' not in st.session_state:
    st.session_state.jump_mid = None
if 'jump_src_chap' not in st.session_state:
    st.session_state.jump_src_chap = None
if 'jump_tgt_chap' not in st.session_state:
    st.session_state.jump_tgt_chap = None
if 'last_src_chap' not in st.session_state:
    st.session_state.last_src_chap = None
if 'last_tgt_chap' not in st.session_state:
    st.session_state.last_tgt_chap = None
if 'show_md' not in st.session_state:
    st.session_state.show_md = False
if 'md_table' not in st.session_state:
    st.session_state.md_table = ""

# ========== 读取 query_params ==========
if "jump_mid" in st.query_params:
    jump_mid = st.query_params["jump_mid"]
    st.query_params.clear()
    st.session_state.jump_mid = jump_mid

# ========== 主界面 ==========
st.title("📜 古籍文本复用比对平台")
st.markdown("逐章对照查看古籍之间的文本承袭关系。下方 **「全书匹配句总览」** 汇总显示所有相似句对，点击 **「📌 跳转」** 可自动切换章节并定位到该句。")

# ========== 侧边栏 ==========
with st.sidebar:
    st.markdown("### ⚙️ 参数设置")
    books = get_indexed_books()
    if not books:
        st.error("未找到索引文件，请先运行 indexer.py")
        st.stop()
    
    source_book = st.selectbox("源书（左栏）", books, index=0 if "史记" in books else 0)
    target_book = st.selectbox("目标书（右栏）", books, index=1 if len(books) > 1 else 0)
    n = st.slider("N-gram 长度", 4, 15, 8, step=1)
    threshold = st.slider("相似度阈值（%）", 0, 100, 40, step=5)
    
    if source_book == target_book:
        st.warning("请选择不同的书籍")
    
    # ====== AI 使用声明生成器 ======
    st.divider()
    st.markdown("### 📋 实验元数据")
    if source_book != target_book:
        match_count = st.session_state.get("current_match_count", 0)
        st.caption(f"**源书**：{source_book}")
        st.caption(f"**目标书**：{target_book}")
        st.caption(f"**N-gram 长度**：{n}")
        st.caption(f"**相似度阈值**：{threshold}%")
        st.caption(f"**匹配句对总数**：{match_count}")
        if match_count > 0:
            st.divider()
            st.markdown("**📄 AI 使用声明（可复制）**")
            ai_declaration = f"""本实验使用 Streamlit 搭建交互界面，核心 N-gram 比对算法由 Python 独立实现。实验数据来源于 CCT 古籍平台，共处理 {source_book} 与 {target_book} 两部文献，在 N={n}、相似度阈值={threshold}% 的参数下，检测到 {match_count} 对匹配句。代码编写过程中，部分 UI 交互代码（如 Streamlit 组件布局、CSS 样式调整）借助 AI 辅助生成，所有核心算法逻辑及参数调优由本人独立完成。"""
            st.code(ai_declaration, language="text")
            st.caption("👆 选中上方文字，按 Ctrl+C 复制，粘贴到报告末尾的「AI 使用声明」部分")
        else:
            st.info("请先选择书籍并完成比对，以生成完整的实验元数据。")
    else:
        st.info("请选择不同的源书和目标书以查看元数据。")

# ========== 主逻辑 ==========
if source_book != target_book:
    with st.spinner("🔄 正在加载索引并执行比对，请稍候..."):
        src_data = load_book_data(source_book)
        tgt_data = load_book_data(target_book)
        src_sents = src_data["sentences"]
        src_idx = src_data["index"]
        src_chapters = src_data.get("chapter_boundaries", [])
        tgt_sents = tgt_data["sentences"]
        tgt_idx = tgt_data["index"]
        tgt_chapters = tgt_data.get("chapter_boundaries", [])
        pairs = find_matching_pairs(src_sents, src_idx, tgt_sents, tgt_idx, n, threshold)
    
    total_matches = len(pairs)
    st.session_state.current_match_count = total_matches
    
    st.subheader(f"📊 {source_book} ↔ {target_book}")
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"<div class='metric-box'>源书总句数：{len(src_sents)}</div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='metric-box'>目标书总句数：{len(tgt_sents)}</div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='metric-box'>全书匹配句对：{total_matches}</div>", unsafe_allow_html=True)
    
    if not pairs:
        st.info("未找到匹配句对，请降低阈值或调整 N-gram 长度。")
    else:
        # ---- 构建全局匹配映射 ----
        src_sent_to_chap = {}
        for chap_id, start, end in src_chapters:
            for i in range(start, end+1):
                src_sent_to_chap[i] = chap_id
        tgt_sent_to_chap = {}
        for chap_id, start, end in tgt_chapters:
            for i in range(start, end+1):
                tgt_sent_to_chap[i] = chap_id
        
        global_match_map = []
        for idx, (s_idx, t_idx, sim) in enumerate(pairs):
            src_chap = src_sent_to_chap.get(s_idx, "未知")
            tgt_chap = tgt_sent_to_chap.get(t_idx, "未知")
            mid = f"g{idx:04d}"
            global_match_map.append({
                "mid": mid,
                "s_idx": s_idx,
                "t_idx": t_idx,
                "sim": sim,
                "src_sent": src_sents[s_idx],
                "tgt_sent": tgt_sents[t_idx],
                "src_chap": src_chap,
                "tgt_chap": tgt_chap
            })
        
        # ---- 处理跳转请求 ----
        if st.session_state.jump_mid is not None:
            jump_item = None
            for item in global_match_map:
                if item["mid"] == st.session_state.jump_mid:
                    jump_item = item
                    break
            if jump_item:
                st.session_state.jump_src_chap = jump_item["src_chap"]
                st.session_state.jump_tgt_chap = jump_item["tgt_chap"]
                st.session_state.jump_mid = None
        
        # ---- 统计摘要 ----
        if total_matches > 0:
            sim_values = [item["sim"] for item in global_match_map]
            max_sim = max(sim_values)
            min_sim = min(sim_values)
            avg_sim = round(sum(sim_values) / len(sim_values), 1)
            src_chaps_with_match = {item["src_chap"] for item in global_match_map if item["src_chap"] != "未知"}
            tgt_chaps_with_match = {item["tgt_chap"] for item in global_match_map if item["tgt_chap"] != "未知"}
            src_chap_count = len(src_chaps_with_match)
            tgt_chap_count = len(tgt_chaps_with_match)
            
            st.divider()
            st.markdown("### 📊 匹配统计摘要")
            col_stat1, col_stat2, col_stat3, col_stat4, col_stat5 = st.columns(5)
            with col_stat1:
                st.metric("最高相似度", f"{max_sim}%")
            with col_stat2:
                st.metric("平均相似度", f"{avg_sim}%")
            with col_stat3:
                st.metric("最低相似度", f"{min_sim}%")
            with col_stat4:
                st.metric("源书匹配章节", src_chap_count)
            with col_stat5:
                st.metric("目标书匹配章节", tgt_chap_count)
            st.caption(f"共 {total_matches} 对匹配句，涉及源书 {src_chap_count} 个章节、目标书 {tgt_chap_count} 个章节。")
        
        # ---- 最长连续匹配片段 ----
        if total_matches > 0:
            sorted_matches = sorted(global_match_map, key=lambda x: x["s_idx"])
            fragments = []
            current_frag = []
            for item in sorted_matches:
                if not current_frag:
                    current_frag.append(item)
                else:
                    prev = current_frag[-1]
                    if (item["s_idx"] == prev["s_idx"] + 1 and 
                        item["t_idx"] == prev["t_idx"] + 1):
                        current_frag.append(item)
                    else:
                        if len(current_frag) >= 2:
                            fragments.append({
                                "start_s": current_frag[0]["s_idx"],
                                "start_t": current_frag[0]["t_idx"],
                                "length": len(current_frag),
                                "items": current_frag.copy()
                            })
                        current_frag = [item]
            if len(current_frag) >= 2:
                fragments.append({
                    "start_s": current_frag[0]["s_idx"],
                    "start_t": current_frag[0]["t_idx"],
                    "length": len(current_frag),
                    "items": current_frag.copy()
                })
            
            if fragments:
                longest = sorted(fragments, key=lambda x: x["length"], reverse=True)[0]
                st.divider()
                st.subheader(f"🔗 最长连续匹配片段（共 {longest['length']} 句）")
                st.caption(f"源书第 {longest['start_s']} 句 至 第 {longest['start_s'] + longest['length'] - 1} 句 ⇔ 目标书第 {longest['start_t']} 句 至 第 {longest['start_t'] + longest['length'] - 1} 句")
                col_left_ex, col_right_ex = st.columns(2, gap="large")
                with col_left_ex:
                    st.markdown(f"**📖 {source_book}**")
                    for idx, item in enumerate(longest["items"]):
                        st.markdown(
                            f'<div style="padding:4px 10px; margin:2px 0; border-left: 3px solid #d4b68a; background-color:#fcf9f2; font-size:14px; line-height:1.8;">'
                            f'<span style="color:#b8a085; font-size:12px;">[{idx+1}] </span>'
                            f'{item["src_sent"][:200]}{"..." if len(item["src_sent"]) > 200 else ""}'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                with col_right_ex:
                    st.markdown(f"**📖 {target_book}**")
                    for idx, item in enumerate(longest["items"]):
                        st.markdown(
                            f'<div style="padding:4px 10px; margin:2px 0; border-left: 3px solid #b8a085; background-color:#fcf9f2; font-size:14px; line-height:1.8;">'
                            f'<span style="color:#b8a085; font-size:12px;">[{idx+1}] </span>'
                            f'{item["tgt_sent"][:200]}{"..." if len(item["tgt_sent"]) > 200 else ""}'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                sims = [item["sim"] for item in longest["items"]]
                st.caption(f"该片段各句相似度：{' → '.join([f'{s}%' for s in sims])}")
            else:
                st.divider()
                st.subheader("🔗 最长连续匹配片段")
                st.info("未检测到连续匹配片段（需要至少2句连续匹配）。")
        
        # ---- 全书匹配句总览 ----
        st.divider()
        st.subheader("📜 全书匹配句总览")
        sorted_items = sorted(global_match_map, key=lambda x: x["sim"], reverse=True)
        
        # 导出功能
        col_export1, col_export2, col_export3 = st.columns([1, 1, 4])
        with col_export1:
            if st.button("📥 导出 CSV", use_container_width=True):
                import io, csv
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["相似度(%)", "源书章节", "目标书章节", "源书句子", "目标书句子"])
                for item in sorted_items:
                    writer.writerow([
                        item["sim"],
                        item["src_chap"],
                        item["tgt_chap"],
                        item["src_sent"].replace("\n", " ").replace("\r", " "),
                        item["tgt_sent"].replace("\n", " ").replace("\r", " ")
                    ])
                csv_bytes = output.getvalue().encode("utf-8-sig")
                st.download_button(
                    label="点击下载 CSV",
                    data=csv_bytes,
                    file_name=f"{source_book}_{target_book}_匹配句对.csv",
                    mime="text/csv; charset=utf-8",
                    use_container_width=True
                )
        with col_export2:
            if st.button("📋 生成 Markdown 表格", use_container_width=True):
                md_lines = ["| 相似度 | 源书章节 | 目标书章节 | 源书句子 | 目标书句子 |"]
                md_lines.append("|--------|----------|----------|----------|----------|")
                for item in sorted_items[:200]:
                    src_text = item["src_sent"][:60].replace("\n", " ").replace("\r", " ") + "..." if len(item["src_sent"]) > 60 else item["src_sent"].replace("\n", " ").replace("\r", " ")
                    tgt_text = item["tgt_sent"][:60].replace("\n", " ").replace("\r", " ") + "..." if len(item["tgt_sent"]) > 60 else item["tgt_sent"].replace("\n", " ").replace("\r", " ")
                    md_lines.append(f"| {item['sim']}% | {item['src_chap']} | {item['tgt_chap']} | {src_text} | {tgt_text} |")
                st.session_state.md_table = "\n".join(md_lines)
                st.session_state.show_md = True
                st.rerun()
        if st.session_state.get("show_md", False) and st.session_state.get("md_table", ""):
            with st.expander("📋 点击复制下方 Markdown 表格（用于报告）"):
                st.code(st.session_state.md_table, language="markdown")
                st.caption("👆 选中上方的表格内容，按 Ctrl+C 复制，然后粘贴到你的 .md 报告文件中")
                if st.button("🔄 关闭表格预览"):
                    st.session_state.show_md = False
                    st.rerun()
        
        # 总览列表
        st.caption(f"共 {total_matches} 对匹配句，按相似度从高到低排序。点击「📌 跳转」自动切换章节并定位。")
        limit = st.session_state.display_limit
        display_items = sorted_items[:limit]
        overview_html = []
        for item in display_items:
            sim = item["sim"]
            src_text = item["src_sent"][:60] + "..." if len(item["src_sent"]) > 60 else item["src_sent"]
            tgt_text = item["tgt_sent"][:60] + "..." if len(item["tgt_sent"]) > 60 else item["tgt_sent"]
            src_chap = item["src_chap"]
            tgt_chap = item["tgt_chap"]
            mid = item["mid"]
            overview_html.append(
                f'<div class="match-item">'
                f'<span class="sim-tag">{sim}%</span>'
                f'<span class="chap-tag">源:{src_chap}</span>'
                f'<span class="chap-tag">→ 目:{tgt_chap}</span>'
                f'<span class="src-text">{src_text}</span>'
                f'<span class="arrow-sym"> ⟷ </span>'
                f'<span class="tgt-text">{tgt_text}</span>'
                f'<a href="?jump_mid={mid}" class="jump-link" style="margin-left:12px;">📌 跳转</a>'
                f'</div>'
            )
        if overview_html:
            st.markdown(
                f'<div style="max-height:500px; overflow-y:auto; border:1px solid #e0d6c8; border-radius:8px; padding:8px 12px; background-color:#fcf9f2;">'
                + ''.join(overview_html) +
                f'</div>',
                unsafe_allow_html=True
            )
        
        col_load1, col_load2, col_load3 = st.columns([1, 1, 2])
        with col_load1:
            if limit < total_matches:
                if st.button(f"📥 加载更多（当前 {limit} / {total_matches}）", use_container_width=True):
                    st.session_state.display_limit = min(limit + 30, total_matches)
                    st.rerun()
        with col_load2:
            if limit > 30:
                if st.button("📤 收起", use_container_width=True):
                    st.session_state.display_limit = 30
                    st.rerun()
        
        # ============================================================
        # 逐章对照查看
        # ============================================================
        st.divider()
        st.subheader("📖 逐章对照查看（带联动跳转）")
        src_chap_ids = [c[0] for c in src_chapters] if src_chapters else ["0000"]
        tgt_chap_ids = [c[0] for c in tgt_chapters] if tgt_chapters else ["0000"]
        
        default_src_idx = 0
        default_tgt_idx = 0
        if st.session_state.jump_src_chap is not None and st.session_state.jump_src_chap in src_chap_ids:
            default_src_idx = src_chap_ids.index(st.session_state.jump_src_chap)
        if st.session_state.jump_tgt_chap is not None and st.session_state.jump_tgt_chap in tgt_chap_ids:
            default_tgt_idx = tgt_chap_ids.index(st.session_state.jump_tgt_chap)
        
        col_left_sel, col_right_sel = st.columns(2)
        with col_left_sel:
            src_selected = st.selectbox(f"📖 {source_book} 章节", src_chap_ids, index=default_src_idx, key="src_chap")
        with col_right_sel:
            tgt_selected = st.selectbox(f"📖 {target_book} 章节", tgt_chap_ids, index=default_tgt_idx, key="tgt_chap")
        
        if src_selected != st.session_state.last_src_chap or tgt_selected != st.session_state.last_tgt_chap:
            st.session_state.jump_mid = None
            st.session_state.jump_src_chap = None
            st.session_state.jump_tgt_chap = None
            st.session_state.last_src_chap = src_selected
            st.session_state.last_tgt_chap = tgt_selected
        
        src_start, src_end = 0, len(src_sents) - 1
        for chap_id, start, end in src_chapters:
            if chap_id == src_selected:
                src_start, src_end = start, end
                break
        tgt_start, tgt_end = 0, len(tgt_sents) - 1
        for chap_id, start, end in tgt_chapters:
            if chap_id == tgt_selected:
                tgt_start, tgt_end = start, end
                break
        
        src_chap_sents = src_sents[src_start:src_end+1]
        tgt_chap_sents = tgt_sents[tgt_start:tgt_end+1]
        
        filtered_data = []
        src_match_map = {}
        tgt_match_map = {}
        for item in global_match_map:
            s_idx = item["s_idx"]
            t_idx = item["t_idx"]
            if src_start <= s_idx <= src_end and tgt_start <= t_idx <= tgt_end:
                mid = item["mid"]
                filtered_data.append({"s_idx": s_idx, "t_idx": t_idx, "sim": item["sim"], "mid": mid})
                src_match_map[s_idx - src_start] = mid
                tgt_match_map[t_idx - tgt_start] = mid
        
        st.markdown(f"<div style='margin: 10px 0; font-size: 15px;'>📌 当前章节匹配句对：<strong>{len(filtered_data)}</strong> 对</div>", unsafe_allow_html=True)
        if len(filtered_data) > 0 and st.session_state.get('last_filtered_len', 0) != len(filtered_data):
            st.session_state.pair_idx = 0
            st.session_state.last_filtered_len = len(filtered_data)
        
        src_hl_local = {i for i in src_match_map.keys()}
        tgt_hl_local = {i for i in tgt_match_map.keys()}
        
        col_left, col_right = st.columns(2, gap="large")
        with col_left:
            st.markdown(f"### 📖 {source_book} (点击↘跳转)")
            if src_chap_sents:
                html = build_chapter_html(src_selected, src_chap_sents, src_hl_local, src_match_map, side="left")
                st.markdown(f'<div class="guwen-box">{html}</div>', unsafe_allow_html=True)
            else:
                st.info("该章节无内容")
        with col_right:
            st.markdown(f"### 📖 {target_book} (锚点目标)")
            if tgt_chap_sents:
                html = build_chapter_html(tgt_selected, tgt_chap_sents, tgt_hl_local, tgt_match_map, side="right")
                st.markdown(f'<div class="guwen-box">{html}</div>', unsafe_allow_html=True)
            else:
                st.info("该章节无内容")
        
        if filtered_data:
            st.divider()
            st.subheader("🔍 匹配对精准导航")
            nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 2])
            with nav_col1:
                if st.button("⬅ 上一匹配句", use_container_width=True):
                    if st.session_state.pair_idx > 0:
                        st.session_state.pair_idx -= 1
                    else:
                        st.session_state.pair_idx = len(filtered_data) - 1
                    st.rerun()
            with nav_col2:
                if st.button("下一匹配句 ➡", use_container_width=True):
                    if st.session_state.pair_idx < len(filtered_data) - 1:
                        st.session_state.pair_idx += 1
                    else:
                        st.session_state.pair_idx = 0
                    st.rerun()
            with nav_col3:
                current_idx = st.session_state.pair_idx
                st.markdown(f"<div style='text-align: center; margin-top: 8px;'>当前查看：第 <strong>{current_idx + 1}</strong> / {len(filtered_data)} 对</div>", unsafe_allow_html=True)
            target_mid = filtered_data[current_idx]["mid"]
            st.components.v1.html(f"""
                <script>
                    (function() {{
                        try {{
                            var target = window.parent.document.getElementById('tgt_{target_mid}');
                            if (target) {{
                                target.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                                target.style.transition = 'background-color 0.3s';
                                target.style.backgroundColor = '#ffdd99';
                                setTimeout(function() {{
                                    target.style.backgroundColor = '#f7e5b0';
                                }}, 800);
                            }}
                        }} catch(e) {{}}
                    }})();
                </script>
            """, height=0, width=0)
        
        with st.expander("📋 查看当前章节匹配句对详情"):
            detail = []
            for data in filtered_data[:100]:
                detail.append({
                    f"{source_book} 句子": src_sents[data["s_idx"]][:150] + "...",
                    f"{target_book} 句子": tgt_sents[data["t_idx"]][:150] + "...",
                    "相似度": f"{data['sim']}%"
                })
            st.dataframe(detail, use_container_width=True)
        
        # ============================================================
        # 动态全局网络图（以当前源书为中心，包含所有书籍）
        # ============================================================
        st.divider()
        st.subheader(f"📈 全局复用网络图（以《{source_book}》为中心）")
        st.caption(f"节点为所有书籍，有向边表示《{source_book}》→ 目标书的匹配句对数。当前参数：N={n}, 阈值={threshold}%")
        
        all_books = get_indexed_books()
        
        src_sents_all = load_book_data(source_book)["sentences"]
        src_idx_all = load_book_data(source_book)["index"]
        
        progress_bar = st.progress(0, text="正在计算各书匹配权重...")
        status_text = st.empty()
        
        weights = {}
        total_books = len(all_books)
        for idx, book in enumerate(all_books):
            if book == source_book:
                progress_bar.progress((idx + 1) / total_books, text=f"跳过 {book}（自身）")
                continue
            status_text.text(f"正在比对：{book} ({idx+1}/{total_books})")
            try:
                tgt_data = load_book_data(book)
                tgt_sents = tgt_data["sentences"]
                tgt_idx = tgt_data["index"]
                matches = find_matching_pairs(src_sents_all, src_idx_all, tgt_sents, tgt_idx, n, threshold)
                weights[book] = len(matches)
            except Exception as e:
                weights[book] = 0
            progress_bar.progress((idx + 1) / total_books, text=f"已完成 {idx+1}/{total_books}")
        
        status_text.text("计算完成，正在绘制网络图...")
        
        G = nx.DiGraph()
        for book in all_books:
            G.add_node(book)
        for book, w in weights.items():
            if w > 0:
                G.add_edge(source_book, book, weight=w)
        
        progress_bar.empty()
        status_text.empty()
        
        if len(G.edges) == 0:
            st.info("当前参数下，源书与其他书籍无匹配关系，请降低阈值或调整N-gram长度。")
        else:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC']
            plt.rcParams['axes.unicode_minus'] = False
            fig, ax = plt.subplots(figsize=(12, 8))  # 宽度12，高度8，整体缩小
            pos = nx.spring_layout(G, seed=42, k=3, iterations=50)
            nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=2000, ax=ax)
            if G.edges:
                weights_list = [d['weight'] for _, _, d in G.edges(data=True)]
                max_weight = max(weights_list) if weights_list else 1
                edge_widths = [1 + 5 * (w / max_weight) for w in weights_list]
                nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True,
                                       arrowsize=20, arrowstyle='->',
                                       width=edge_widths, ax=ax)
            nx.draw_networkx_labels(G, pos, font_size=8, font_family='SimHei', ax=ax)
            edge_labels = {(u, v): str(d['weight']) for u, v, d in G.edges(data=True)}
            nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7, ax=ax)
            ax.set_title(f"以《{source_book}》为中心的全局复用网络\n(N={n}, 阈值={threshold}%)", fontsize=14)
            ax.axis('off')
            st.pyplot(fig)
            st.caption(f"共 {len(G.edges)} 条有效边，最大匹配权重：{max_weight}，平均权重：{sum(weights_list)/len(weights_list):.1f}")

else:
    st.info("请选择不同的源书和目标书")