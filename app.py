import time
from html import escape

import streamlit as st

from ask import exam_questions
from rag import ask, chat_model, db, embed_model, min_score, top_k

st.set_page_config(page_title="HR Policy Assistant", page_icon="📘", layout="centered")

topics = [
    (":material/beach_access:", "Privilege leave"),
    (":material/badge:", "Probation period"),
    (":material/health_and_safety:", "Health insurance"),
    (":material/receipt_long:", "GST rate"),
    (":material/child_care:", "Maternity leave"),
]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.stApp, .stApp p, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp label,
.stApp button p, .stApp input, .stApp textarea { font-family: 'Inter', system-ui, -apple-system, sans-serif !important; }

.stApp { background: #f5f7fb; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2.6rem; padding-bottom: 7rem; max-width: 880px; }

@keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }

/* welcome banner */
.hero { position: relative; overflow: hidden; border-radius: 22px; padding: 2rem 2rem 1.6rem; color: #fff;
        background: linear-gradient(135deg, #0f2a4a 0%, #18457a 55%, #1f7a8c 100%);
        box-shadow: 0 18px 40px -18px rgba(15, 42, 74, .55); animation: rise .5s ease both; }
.hero::after { content: ""; position: absolute; right: -80px; top: -80px; width: 260px; height: 260px;
               border-radius: 50%; background: radial-gradient(circle, rgba(255,255,255,.16), transparent 70%); }
.hero .badge { display: inline-block; font-size: .74rem; font-weight: 600; letter-spacing: .04em; text-transform: uppercase;
               background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.22); border-radius: 999px; padding: .25rem .7rem; }
.hero h1 { color: #fff !important; font-size: 2.05rem !important; font-weight: 800 !important; line-height: 1.2; margin: .9rem 0 .5rem; padding: 0; }
.hero p { color: rgba(255,255,255,.86) !important; font-size: 1rem; line-height: 1.6; max-width: 640px; margin: 0; }
.hero p b { color: #fff; }
.hero-stats { display: flex; gap: .7rem; flex-wrap: wrap; margin-top: 1.4rem; }
.hero-stats div { flex: 1 1 140px; background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.18);
                  border-radius: 14px; padding: .7rem .9rem; backdrop-filter: blur(6px); }
.hero-stats b { display: block; font-size: 1.35rem; font-weight: 700; color: #fff; }
.hero-stats span { font-size: .8rem; color: rgba(255,255,255,.78); }

.label { font-size: .78rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: #6b7686; margin: 1.8rem 0 .7rem; }

/* question cards on the welcome screen */
[class*="st-key-try"] button { min-height: 76px; justify-content: flex-start; text-align: left; background: #fff;
    border: 1px solid #e3e8f0; border-radius: 14px; padding: .8rem 1rem; box-shadow: 0 1px 2px rgba(16,24,40,.04);
    transition: all .18s ease; }
[class*="st-key-try"] button:hover { border-color: #8fb3e3; box-shadow: 0 8px 20px -10px rgba(24,69,122,.35); transform: translateY(-2px); }
[class*="st-key-try"] button p { font-size: .93rem; color: #1b2a3d; line-height: 1.4; white-space: normal !important;
    overflow: visible !important; text-overflow: clip !important; text-align: left; }
[class*="st-key-try"] button > div { justify-content: flex-start; width: 100%; }
[class*="st-key-try"] button span[data-testid="stIconMaterial"] { color: #1f7a8c; }

/* how it works */
.steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: .8rem; }
.step { background: #fff; border: 1px solid #e3e8f0; border-radius: 14px; padding: 1rem; }
.step .num { display: inline-flex; width: 28px; height: 28px; border-radius: 8px; align-items: center; justify-content: center;
             background: #e8f1fb; color: #18457a; font-weight: 700; font-size: .85rem; }
.step b { display: block; margin: .55rem 0 .2rem; color: #0f2a4a; }
.step span { font-size: .85rem; color: #5b6778; line-height: 1.5; }

/* slim header once the chat starts */
.topbar { display: flex; align-items: center; gap: .8rem; padding: .9rem 1.1rem; border-radius: 16px; color: #fff;
          background: linear-gradient(135deg, #0f2a4a 0%, #18457a 60%, #1f7a8c 100%); margin-bottom: 1.2rem; }
.topbar .logo { font-size: 1.5rem; }
.topbar b { display: block; font-size: 1.05rem; }
.topbar span { font-size: .82rem; color: rgba(255,255,255,.8); }

/* chat */
[data-testid="stChatMessage"] { background: transparent !important; padding: .3rem 0; }
.q-bubble { display: inline-block; background: #e8f1fb; color: #0f2a4a; border-radius: 14px 14px 14px 4px;
            padding: .65rem .95rem; font-weight: 500; line-height: 1.5; }
.card { background: #fff; border: 1px solid #e3e8f0; border-radius: 16px; padding: 1.1rem 1.2rem;
        box-shadow: 0 10px 30px -18px rgba(16,24,40,.25); animation: rise .35s ease both; }
.pill { display: inline-flex; align-items: center; gap: .3rem; font-size: .74rem; font-weight: 700; border-radius: 999px; padding: .2rem .65rem; }
.pill.ok { color: #16653a; background: #e6f6ec; border: 1px solid #bfe5cc; }
.pill.no { color: #a12a2a; background: #fdeeee; border: 1px solid #f3caca; }
.answer { font-size: 1.25rem; font-weight: 600; color: #0f2a4a; line-height: 1.45; margin: .55rem 0 .8rem; overflow-wrap: anywhere; }
.not-found { font-size: 1.25rem; font-weight: 700; color: #a12a2a; margin: .55rem 0 .3rem; }
.why { color: #6b7686; font-size: .9rem; }
.hint { color: #8a94a3; font-size: .82rem; margin-top: .5rem; }
.ref { display: flex; align-items: center; justify-content: space-between; gap: .8rem; flex-wrap: wrap;
       background: #f5f8fc; border: 1px solid #e3e8f0; border-radius: 12px; padding: .6rem .8rem; margin-top: .5rem; }
.ref small { display: block; font-size: .7rem; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; color: #8a94a3; }
.ref .section { font-size: .92rem; font-weight: 600; color: #18457a; overflow-wrap: anywhere; }
.ref a { flex-shrink: 0; background: #18457a; color: #fff !important; text-decoration: none; font-size: .82rem; font-weight: 600;
         border-radius: 9px; padding: .4rem .75rem; transition: background .15s ease; }
.ref a:hover { background: #1f7a8c; }
.quote { border-left: 3px solid #1f7a8c; margin: .7rem 0 .2rem; padding: .15rem .9rem; color: #4a5566;
         font-size: .92rem; line-height: 1.55; font-style: italic; overflow-wrap: anywhere; }
.meta { color: #8a94a3; font-size: .78rem; margin-top: .7rem; }
.source-head { font-size: .85rem; color: #0f2a4a; margin-top: .6rem; }
.source-text { font-size: .8rem; color: #5b6778; white-space: pre-wrap; }

/* sidebar */
[data-testid="stSidebar"] { background: #fff; border-right: 1px solid #e6ebf2; }
.brand { display: flex; align-items: center; gap: .7rem; margin-bottom: 1.2rem; }
.brand .logo { width: 42px; height: 42px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
               font-size: 1.3rem; background: linear-gradient(135deg, #18457a, #1f7a8c); }
.brand b { display: block; color: #0f2a4a; font-size: 1rem; }
.brand span { font-size: .8rem; color: #6b7686; }
[class*="st-key-q"] button { justify-content: flex-start; border-radius: 10px; border: 1px solid #eef1f6; background: #fafbfd; }
[class*="st-key-q"] button:hover { border-color: #8fb3e3; background: #f2f7fd; }
.sys div { display: flex; justify-content: space-between; gap: .5rem; font-size: .8rem; padding: .35rem 0; border-bottom: 1px dashed #e6ebf2; }
.sys span { color: #6b7686; }
.sys b { color: #1b2a3d; font-weight: 600; text-align: right; overflow-wrap: anywhere; }

/* chat input */
[data-testid="stChatInput"] { border-radius: 16px !important; box-shadow: 0 10px 30px -14px rgba(16,24,40,.3); }

@media (max-width: 640px) {
  .block-container { padding: 4rem .9rem 7rem; }
  .hero { padding: 1.4rem 1.2rem 1.2rem; border-radius: 18px; }
  .hero h1 { font-size: 1.5rem !important; }
  .hero p { font-size: .92rem; }
  .hero-stats div { flex: 1 1 90px; padding: .55rem .7rem; }
  .hero-stats b { font-size: 1.1rem; }
  .steps { grid-template-columns: 1fr; }
  .answer, .not-found { font-size: 1.1rem; }
  .card { padding: .95rem 1rem; }
  .ref a { width: 100%; text-align: center; }
}
</style>
""", unsafe_allow_html=True)


def pick(question):
    st.session_state.picked = question


def new_chat():
    st.session_state.history = []


def show_answer(result):
    if result["found"]:
        html = f'<div class="card"><span class="pill ok">✓ Found in the manual</span><div class="answer">{escape(result["answer"])}</div>'
        for c in result["citations"]:
            section = escape(c["section"].replace(" > ", " › "))
            quote = escape(c["quote"].lstrip("-> "))
            html += (
                f'<div class="ref"><div><small>Reference</small><div class="section">{section} · page {c["page"]}</div></div>'
                f'<a href="app/static/hr_manual.pdf#page={c["page"]}" target="_blank">View page {c["page"]} ↗</a></div>'
                f'<div class="quote">“{quote}”</div>'
            )
    else:
        html = (
            f'<div class="card"><span class="pill no">✕ Not in the manual</span><div class="not-found">Not found</div>'
            f'<div class="why">{escape(result["reason"].capitalize())}.</div>'
            f'<div class="hint">Try rephrasing, or ask about leave, probation, travel or conduct.</div>'
        )

    best = result["sources"][0] if result["sources"] else None
    if best and "seconds" in result:
        html += f'<div class="meta">⚡ answered in {result["seconds"]}s · best match {best["score"]} (page {best["page"]})</div>'
    st.markdown(html + "</div>", unsafe_allow_html=True)

    with st.expander(f"Sources checked ({len(result['sources'])} chunks)", icon=":material/search:"):
        for s in result["sources"]:
            text = s["text"].split("\n", 1)[-1]
            st.markdown(
                f'<div class="source-head"><b>Page {s["page"]}</b> · {escape(s["section"])} · score {s["score"]}</div>'
                f'<div class="source-text">{escape(text[:450])}...</div>',
                unsafe_allow_html=True,
            )


if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="logo">📘</div><div><b>HR Policy Assistant</b><span>Enso Group HR Manual</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="label" style="margin-top:0">Exam questions</div>', unsafe_allow_html=True)
    for i, q in enumerate(exam_questions):
        icon, label = topics[i]
        st.button(f"Q{i + 1} · {label}", key=f"q{i}", icon=icon, help=q, on_click=pick, args=(q,), width="stretch")

    st.markdown('<div class="label">System</div>', unsafe_allow_html=True)
    st.markdown(f"""
<div class="sys">
  <div><span>Document</span><b>79 pages</b></div>
  <div><span>Chunks in ChromaDB</span><b>{db._collection.count()}</b></div>
  <div><span>Embeddings</span><b>{embed_model}</b></div>
  <div><span>LLM (Groq)</span><b>{chat_model}</b></div>
  <div><span>Top k · min score</span><b>{top_k} · {min_score}</b></div>
</div>
""", unsafe_allow_html=True)
    st.write("")
    st.button("New chat", icon=":material/add_comment:", on_click=new_chat, width="stretch")

question = st.chat_input("Ask about leave, probation, travel, conduct...") or st.session_state.pop("picked", None)

if not st.session_state.history and not question:
    st.markdown(f"""
<div class="hero">
  <span class="badge">Enso Group · HR Policy Manual</span>
  <h1>Hi there 👋 How can I help you today?</h1>
  <p>Ask anything about leave, probation, travel or conduct. I answer only from the official HR manual and show the
  exact section and page, or tell you honestly when it is <b>not in the manual</b>.</p>
  <div class="hero-stats">
    <div><b>79</b><span>pages read</span></div>
    <div><b>{db._collection.count()}</b><span>searchable chunks</span></div>
    <div><b>16/16</b><span>test questions passed</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="label">Try an exam question</div>', unsafe_allow_html=True)
    # one row of two cards at a time so phones show them in order
    for row in range(0, len(exam_questions), 2):
        cols = st.columns(2)
        for i in range(row, min(row + 2, len(exam_questions))):
            with cols[i - row]:
                st.button(exam_questions[i], key=f"try{i}", icon=topics[i][0], on_click=pick, args=(exam_questions[i],), width="stretch")

    st.markdown("""
<div class="label">How it works</div>
<div class="steps">
  <div class="step"><span class="num">1</span><b>Search</b><span>Finds the 5 most relevant passages of the manual in ChromaDB.</span></div>
  <div class="step"><span class="num">2</span><b>Verify</b><span>Checks the answer is really written in those passages, nothing from outside.</span></div>
  <div class="step"><span class="num">3</span><b>Cite</b><span>Shows the policy, page and exact quote, or says Not found.</span></div>
</div>
""", unsafe_allow_html=True)
else:
    st.markdown(
        '<div class="topbar"><div class="logo">📘</div><div><b>HR Policy Assistant</b>'
        '<span>Answers from the Enso Group HR Policy Manual, with section and page</span></div></div>',
        unsafe_allow_html=True,
    )

for item in st.session_state.history:
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(f'<div class="q-bubble">{escape(item["question"])}</div>', unsafe_allow_html=True)
    with st.chat_message("assistant", avatar=":material/menu_book:"):
        show_answer(item)

if question:
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(f'<div class="q-bubble">{escape(question)}</div>', unsafe_allow_html=True)
    with st.chat_message("assistant", avatar=":material/menu_book:"):
        try:
            start = time.time()
            with st.spinner("searching the manual..."):
                result = ask(question)
            result["seconds"] = round(time.time() - start, 1)
        except Exception:
            result = None
            st.error("couldn't reach the model right now, please try again in a minute")
        if result:
            show_answer(result)
            st.session_state.history.append(result)
