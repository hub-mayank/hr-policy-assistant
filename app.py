from html import escape

import streamlit as st

from ask import exam_questions
from rag import ask, chat_model, db, embed_model, min_score, top_k

st.set_page_config(page_title="HR Policy Assistant", page_icon="📘", layout="centered")

st.markdown("""
<style>
.block-container { padding-top: 2.2rem; max-width: 820px; }
.hero { border-bottom: 1px solid #e3e8ef; padding-bottom: 1rem; margin-bottom: 1.2rem; }
.hero h1 { font-size: 2rem; margin: 0; color: #0f2a4a; }
.hero p { color: #5b6778; margin: .35rem 0 0; font-size: .98rem; }
.answer { font-size: 1.08rem; line-height: 1.55; color: #14202e; }
.ref { display: inline-block; background: #e8f1fb; color: #0b4f8a; border: 1px solid #c9def5;
       border-radius: 8px; padding: .3rem .65rem; margin: .55rem 0 .3rem; font-size: .88rem; }
.quote { border-left: 3px solid #9cc3ea; padding: .25rem .8rem; color: #4a5566;
         font-style: italic; font-size: .92rem; margin-bottom: .4rem; }
.not-found { display: inline-block; background: #fdeeee; color: #a12a2a; border: 1px solid #f3caca;
             border-radius: 8px; padding: .35rem .8rem; font-weight: 600; font-size: 1.05rem; }
.why { color: #7a8594; font-size: .85rem; margin-top: .45rem; }
.source-head { font-size: .85rem; color: #0f2a4a; margin-top: .6rem; }
.source-text { font-size: .8rem; color: #5b6778; white-space: pre-wrap; }
</style>
""", unsafe_allow_html=True)


def show_answer(result):
    if result["found"]:
        st.markdown(f'<div class="answer">{escape(result["answer"])}</div>', unsafe_allow_html=True)
        for c in result["citations"]:
            st.markdown(
                f'<div class="ref">📄 <b>Reference:</b> {escape(c["section"])} &nbsp;·&nbsp; page {c["page"]}</div>'
                f'<div class="quote">"{escape(c["quote"])}"</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown('<div class="not-found">Not found</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="why">{escape(result["reason"])}</div>', unsafe_allow_html=True)

    with st.expander(f"Sources checked ({len(result['sources'])} chunks)"):
        for s in result["sources"]:
            text = s["text"].split("\n", 1)[-1]
            st.markdown(
                f'<div class="source-head"><b>Page {s["page"]}</b> · {escape(s["section"])} · score {s["score"]}</div>'
                f'<div class="source-text">{escape(text[:450])}...</div>',
                unsafe_allow_html=True,
            )


with st.sidebar:
    st.subheader("Exam questions")
    picked = None
    for i, q in enumerate(exam_questions):
        if st.button(f"Q{i + 1}. {q}", key=f"q{i}", use_container_width=True):
            picked = q

    st.subheader("About")
    st.markdown(f"""
- **Document:** Enso Group HR Policy Manual (79 pages)
- **Chunks in ChromaDB:** {db._collection.count()}
- **Embeddings:** `{embed_model}`
- **LLM:** `{chat_model}` (Groq)
- **Top k:** {top_k} · **min score:** {min_score}
""")

    if st.button("Clear chat", use_container_width=True):
        st.session_state.history = []

st.markdown("""
<div class="hero">
  <h1>📘 HR Policy Assistant</h1>
  <p>Ask anything about the Enso Group HR Policy Manual. Every answer comes with the policy section and page
  it was taken from, and it replies <b>Not found</b> when the manual does not cover the question.</p>
</div>
""", unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state.history = []

for item in st.session_state.history:
    with st.chat_message("user"):
        st.write(item["question"])
    with st.chat_message("assistant"):
        show_answer(item)

question = st.chat_input("Ask about leave, probation, travel, conduct...") or picked

if question:
    with st.chat_message("user"):
        st.write(question)
    with st.chat_message("assistant"):
        with st.spinner("searching the manual..."):
            result = ask(question)
        show_answer(result)
    st.session_state.history.append(result)
