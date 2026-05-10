import streamlit as st
from langchain_core.messages import HumanMessage
import os, sys

sys.path.append(os.path.dirname(__file__))
from back_agentic import graphflow

st.set_page_config(
    page_title="Medical Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed"
)
st.markdown("""
<style>
/* Progress bar label */
[data-testid="stProgressBar"] ~ p,
div.stProgress p {
    color: #00e5c0 !important;
    font-weight: 500 !important;
}

/* Progress bar track */
[data-testid="stProgressBar"] {
    background: rgba(0,229,192,0.1) !important;
    border-radius: 10px !important;
}

/* Progress bar fill */
[data-testid="stProgressBar"] > div {
    background: linear-gradient(90deg, #00e5c0, #00b89a) !important;
    border-radius: 10px !important;
}

/* Expander header text */
[data-testid="stExpander"] summary p {
    color: #6a90b8 !important;
    font-size: 0.85rem !important;
}
[data-testid="stExpander"] summary:hover p {
    color: #00e5c0 !important;
}

/* Log code block */
[data-testid="stExpander"] pre,
[data-testid="stExpander"] code {
    background: #030c18 !important;
    color: #00e5c0 !important;
    border: 1px solid rgba(0,229,192,0.12) !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=Playfair+Display:wght@400;600&display=swap');

:root {
    --navy:      #040d1a;
    --card:      #071225;
    --card2:     #0a1a30;
    --teal:      #00e5c0;
    --teal-dim:  #00b89a;
    --gold:      #f0c060;
    --text:      #ddeeff;
    --muted:     #6a90b8;
    --border:    rgba(0,229,192,0.18);
}

/* Reset background — remove any image bleeding through */
.stApp, .stApp > * {
    background: var(--navy) !important;
    font-family: 'Sora', sans-serif !important;
}

/* Remove default Streamlit padding */
.block-container {
    padding: 2rem 3rem !important;
    max-width: 1100px !important;
}

/* ── Hero ── */
.hero {
    background: linear-gradient(135deg, #071830 0%, #0a2040 50%, #061525 100%);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 44px 52px;
    margin-bottom: 28px;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -80px; right: -80px;
    width: 320px; height: 320px;
    background: radial-gradient(circle, rgba(0,229,192,0.07) 0%, transparent 65%);
    pointer-events: none;
}
.hero::after {
    content: '';
    position: absolute;
    bottom: -50px; left: 20%;
    width: 250px; height: 250px;
    background: radial-gradient(circle, rgba(240,192,96,0.04) 0%, transparent 65%);
    pointer-events: none;
}
.hero-icon {
    font-size: 2.4rem;
    margin-bottom: 8px;
    display: block;
}
.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.6rem;
    font-weight: 600;
    color: #ffffff;
    margin: 0 0 6px 0;
    line-height: 1.2;
}
.hero-title em {
    color: var(--teal);
    font-style: normal;
}
.hero-sub {
    font-size: 0.85rem;
    color: var(--muted);
    font-weight: 300;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin: 0 0 28px 0;
}
.pubmed-box {
    background: rgba(0,229,192,0.06);
    border: 1px solid rgba(0,229,192,0.2);
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 24px;
}
.pubmed-box .label {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--teal);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 6px;
}
.pubmed-box p {
    font-size: 0.9rem;
    color: #9ab8d8;
    line-height: 1.7;
    margin: 0;
}
.pubmed-box p strong {
    color: #ddeeff;
    font-weight: 500;
}
.badges {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}
.badge {
    background: rgba(0,229,192,0.08);
    border: 1px solid rgba(0,229,192,0.2);
    color: var(--teal);
    border-radius: 30px;
    padding: 5px 14px;
    font-size: 0.75rem;
    font-weight: 500;
    letter-spacing: 0.3px;
}

/* ── Input label ── */
.stTextArea > label {
    color: var(--muted) !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.5px !important;
    font-family: 'Sora', sans-serif !important;
}
.stTextArea textarea {
    background: var(--card2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    color: #ddeeff !important;
    font-family: 'Sora', sans-serif !important;
    font-size: 0.95rem !important;
    caret-color: var(--teal) !important;
}
.stTextArea textarea::placeholder { color: #3a5878 !important; }
.stTextArea textarea:focus {
    border-color: var(--teal) !important;
    box-shadow: 0 0 0 3px rgba(0,229,192,0.08) !important;
}

/* ── Button ── */
.stButton > button {
    background: linear-gradient(135deg, #00e5c0 0%, #00b89a 100%) !important;
    color: #040d1a !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    padding: 12px 36px !important;
    box-shadow: 0 4px 20px rgba(0,229,192,0.2) !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px rgba(0,229,192,0.3) !important;
}

/* ── Metrics ── */
[data-testid="metric-container"] {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: 22px 26px !important;
}
[data-testid="stMetricLabel"] p {
    color: var(--muted) !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 1.2px !important;
    font-family: 'Sora', sans-serif !important;
}
[data-testid="stMetricValue"] {
    color: var(--teal) !important;
    font-family: 'Playfair Display', serif !important;
    font-size: 2.2rem !important;
}

/* ── Markdown text ── */
.stMarkdown p  { color: #9ab8d8 !important; line-height: 1.8 !important; }
.stMarkdown li { color: #9ab8d8 !important; line-height: 1.8 !important; }
.stMarkdown h1, .stMarkdown h2 {
    color: #ffffff !important;
    font-family: 'Playfair Display', serif !important;
    font-weight: 600 !important;
}
.stMarkdown h3, .stMarkdown h4 {
    color: var(--teal) !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 600 !important;
}
.stMarkdown strong { color: #ddeeff !important; }
.stMarkdown a     { color: var(--teal) !important; }

/* ── Summary card ── */
.summary-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 32px 40px;
    margin-top: 12px;
}
.summary-card-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.4rem;
    color: var(--teal);
    margin: 0 0 22px 0;
    padding-bottom: 14px;
    border-bottom: 1px solid var(--border);
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--card2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    margin-bottom: 8px !important;
}
[data-testid="stExpander"] summary {
    color: #9ab8d8 !important;
    font-size: 0.88rem !important;
}
[data-testid="stExpander"] summary:hover { color: var(--teal) !important; }
[data-testid="stExpander"] p { color: #7a9dbf !important; }

/* ── Progress bar ── */
[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, var(--teal), var(--teal-dim)) !important;
}

/* ── Code block (logs) ── */
.stCode, code, pre {
    background: #030c18 !important;
    color: var(--teal) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    font-size: 0.8rem !important;
}

/* ── Divider ── */
hr { border-color: rgba(0,229,192,0.1) !important; }

/* ── Link button ── */
.stLinkButton a {
    background: rgba(0,229,192,0.08) !important;
    color: var(--teal) !important;
    border: 1px solid rgba(0,229,192,0.25) !important;
    border-radius: 8px !important;
    font-size: 0.82rem !important;
}

/* ── Alert ── */
[data-testid="stAlert"] {
    background: rgba(7,18,37,0.9) !important;
    border-color: var(--border) !important;
    border-radius: 12px !important;
}
[data-testid="stAlert"] p { color: var(--muted) !important; }

/* ── Section heading ── */
h3 { color: #ffffff !important; font-family: 'Playfair Display', serif !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--navy); }
::-webkit-scrollbar-thumb { background: #0e2a45; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--teal-dim); }
</style>
""", unsafe_allow_html=True)

# ── Hero Section ─────────────────────────────────────────────
import streamlit.components.v1 as components

components.html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=Playfair+Display:wght@400;600&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body { background: transparent; font-family: 'Sora', sans-serif; }

.hero {
    background: linear-gradient(135deg, #071830 0%, #0a2040 50%, #061525 100%);
    border: 1px solid rgba(0,229,192,0.18);
    border-radius: 20px;
    padding: 40px 48px;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -80px; right: -80px;
    width: 320px; height: 320px;
    background: radial-gradient(circle, rgba(0,229,192,0.07) 0%, transparent 65%);
    pointer-events: none;
}
.hero-icon  { font-size: 2rem; margin-bottom: 8px; display: block; }
.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.4rem;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 6px;
    line-height: 1.2;
}
.hero-title em { color: #00e5c0; font-style: normal; }
.hero-sub {
    font-size: 0.78rem;
    color: #6a90b8;
    font-weight: 300;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    margin-bottom: 28px;
}
.pubmed-box {
    background: rgba(0,229,192,0.06);
    border: 1px solid rgba(0,229,192,0.2);
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 22px;
}
.pubmed-box .label {
    font-size: 0.68rem;
    font-weight: 600;
    color: #00e5c0;
    text-transform: uppercase;
    letter-spacing: 1.8px;
    margin-bottom: 8px;
}
.pubmed-box p {
    font-size: 0.88rem;
    color: #8aadcc;
    line-height: 1.75;
}
.pubmed-box strong { color: #ddeeff; font-weight: 500; }
.badges { display: flex; gap: 8px; flex-wrap: wrap; }
.badge {
    background: rgba(0,229,192,0.08);
    border: 1px solid rgba(0,229,192,0.22);
    color: #00e5c0;
    border-radius: 30px;
    padding: 5px 14px;
    font-size: 0.73rem;
    font-weight: 500;
    letter-spacing: 0.3px;
}
</style>

<div class="hero">
    <span class="hero-icon">🔬</span>
    <p class="hero-title">Medical <em>Research</em> Assistant</p>
    <p class="hero-sub">Agentic AI &nbsp;·&nbsp; Evidence-Based &nbsp;·&nbsp; PubMed Powered</p>

    <div class="pubmed-box">
        <div class="label">📚 What is PubMed?</div>
        <p>
            <strong>PubMed</strong> is the world's largest <strong>free database of biomedical
            literature</strong>, maintained by the <strong>US National Library of Medicine (NLM)</strong>.
            It indexes over <strong>36 million peer-reviewed articles</strong> covering medicine,
            clinical trials, pharmacology, and healthcare. This assistant retrieves papers
            directly from PubMed and grounds every answer in cited evidence —
            <strong>no hallucinations, only real research.</strong>
        </p>
    </div>

    <div class="badges">
        <span class="badge">🧬 36M+ Research Papers</span>
        <span class="badge">✅ Evidence-Backed</span>
        <span class="badge">🔄 Agentic Multi-Step Retrieval</span>
        <span class="badge">📋 PMID Citations</span>
        <span class="badge">🏥 Clinical Grade</span>
        <span class="badge">🤖 LLM Reasoning</span>
    </div>
</div>
""", height=360)

# ── Input ────────────────────────────────────────────────────
question = st.text_area(
    label="**🔍 Ask a Medical Research Question**",
    placeholder="e.g.  What are the targeted therapy options for lung cancer patients with hypertension?",
    height=115
)

col1, col2 = st.columns([1, 6])
with col1:
    submit = st.button("🔍  Search PubMed", type="primary", use_container_width=True)

# ── Pipeline ─────────────────────────────────────────────────
if submit and question.strip():

    Query = {"messages": [HumanMessage(content=question)]}

    progress  = st.progress(0, text="Initialising...")
    status    = st.empty()
    logs      = st.expander("📋 Pipeline logs", expanded=False)
    log_lines = []
    final_state = {}

    steps = {
        "Medical Planner-Natural Language to Clinical Subqueries": (12,  "🧠 Planning clinical queries..."),
        "API CALL-Fetch PubMed Research Papers"                  : (28,  "📡 Fetching PubMed papers..."),
        "XML PARSING-Build Structured LangChain Documents"       : (42,  "📄 Parsing XML..."),
        "Keeps Filtered Documents"                               : (54,  "🗂 Filtering by date..."),
        "Keeps Highly Releavnt Documents"                        : (66,  "🎯 Relevance filtering..."),
        "Build Contextual Documents"                             : (76,  "📚 Building context..."),
        "Build Clinical Answer"                                  : (85,  "⚕️  Reasoning over evidence..."),
        "Answer is Grounded"                                     : (93,  "✅ Validating answer..."),
        "Generate Final response"                                : (100, "✨ Generating summary..."),
    }

    try:
        for chunk in graphflow.stream(Query):
            for node_name, node_output in chunk.items():
                pct, msg = steps.get(node_name, (50, f"Running {node_name}..."))
                progress.progress(pct, text=f"⏳ {msg}")
                status.markdown(
                    f"<p style='color:#00e5c0;background:rgba(0,229,192,0.06);"
                    f"border:1px solid rgba(0,229,192,0.2);border-radius:8px;"
                    f"padding:8px 14px;margin:0;font-size:0.85rem;'>"
                    f"✓ &nbsp; {node_name}</p>",
                    unsafe_allow_html=True
                )
                final_state.update(node_output)

                log_lines.append(f"✓ {node_name}")
                if "search_queries" in node_output:
                    for i, q in enumerate(node_output["search_queries"], 1):
                        log_lines.append(f"   {i}. {q}")
                if "documents" in node_output:
                    log_lines.append(f"   Documents created  : {len(node_output['documents'])}")
                if "filtered_documents" in node_output:
                    log_lines.append(f"   After date filter  : {len(node_output['filtered_documents'])}")
                if "relevant_documents" in node_output:
                    log_lines.append(f"   Relevant papers    : {len(node_output['relevant_documents'])}")
                if "validation" in node_output:
                    log_lines.append(f"   Validation         : {node_output['validation']}")

                with logs:
                    st.code("\n".join(log_lines))

    except Exception as e:
        import re
        progress.empty()
        status.empty()
        err = str(e)
        if "rate_limit_exceeded" in err or "429" in err:
            wait = re.search(r'try again in (.+?)\.', err)
            wait_str = wait.group(1) if wait else "a few minutes"
            st.error(f"⚠️ **Rate limit reached.** Please try again in `{wait_str}`.")
        else:
            st.error(f"❌ Error: {err}")
        st.stop()

    progress.empty()
    status.empty()

    # ── Results ──────────────────────────────────────────────
    relevant_docs  = final_state.get("relevant_documents", [])
    validation     = final_state.get("validation", "")
    retry_count    = final_state.get("retry_count", 0)
    final_response = final_state.get("final_response", "")

    if final_response:
        st.divider()

        # Metrics
        val_label = "PASS" if "FAIL" not in validation.upper() else "FAIL"
        m1, m2, m3 = st.columns(3)
        m1.metric("📄 Papers Used",    len(relevant_docs))
        m2.metric("✅ Validation",      val_label)
        m3.metric("🔄 Retrieval Loops", retry_count + 1)

        # Summary
        st.markdown('<div class="summary-card">', unsafe_allow_html=True)
        st.markdown('<p class="summary-card-title">📋 Clinical Summary</p>', unsafe_allow_html=True)
        st.markdown(final_response)
        st.markdown('</div>', unsafe_allow_html=True)

        # Papers
        if relevant_docs:
            st.divider()
            st.markdown(f"### 🗂 Source Papers &nbsp; `{len(relevant_docs)} papers`")
            for doc in relevant_docs:
                with st.expander(
                    f"PMID {doc.metadata['pmid']}  ·  {doc.metadata.get('year','')}  ·  {doc.metadata['title'][:70]}"
                ):
                    c1, c2 = st.columns(2)
                    c1.markdown(f"**Journal:** {doc.metadata.get('journal','N/A')}")
                    c1.markdown(f"**Year:** {doc.metadata.get('year','N/A')}")
                    c2.markdown(f"**Authors:** {doc.metadata.get('authors','N/A')[:80]}")
                    st.markdown(f"**Abstract:** {doc.page_content[:400]}...")
                    st.link_button(
                        "🔗 View on PubMed",
                        f"https://pubmed.ncbi.nlm.nih.gov/{doc.metadata['pmid']}"
                    )
    else:
        st.warning("No response generated. Try rephrasing your clinical question.")

elif submit and not question.strip():
    st.warning("Please enter a clinical question.")