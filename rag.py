import os
import re
import time
from difflib import SequenceMatcher

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_chroma import Chroma

load_dotenv()

embed_model = os.getenv("EMBED_MODEL", "gemini-embedding-001")
chat_model = os.getenv("CHAT_MODEL", "openai/gpt-oss-120b")
db_path = "db"
top_k = 5
# best chunk below this score means the manual doesn't talk about it at all
min_score = 0.62
not_found = "Not found"


class Citation(BaseModel):
    page: int = Field(description="page number from the [section | page N] label of the chunk used")
    quote: str = Field(description="exact sentence copied word for word from that chunk")


class Answer(BaseModel):
    found: bool = Field(description="true only if the context clearly answers the question")
    answer: str = Field(description="short answer from the context, or exactly 'Not found'")
    citations: list[Citation] = Field(description="where the answer is, empty if not found")


prompt = ChatPromptTemplate.from_messages([
    ("system", """You answer employee questions using only the Enso Group HR Policy Manual.

Rules:
- Use only the context below. Do not use outside knowledge, Indian law or general facts, even if you know them.
- If the context does not clearly state the answer to the exact question asked, set found to false and answer exactly "Not found".
- A related topic is not an answer. If the question asks for an amount, rate, name or date and the context does not give that exact value, it is "Not found".
- If the question has more than one part, answer the parts the context covers and write "Not found" for the rest.
- Keep the answer short and specific. Write numbers exactly as the context writes them.
- For every fact in the answer add a citation with its page and a quote copied word for word from the context.

Context:
{context}"""),
    ("human", "{question}"),
])

if not os.path.exists(db_path):
    raise SystemExit("db folder not found, run python ingest.py first")

embeddings = GoogleGenerativeAIEmbeddings(model=embed_model)
db = Chroma(collection_name="hr_manual", embedding_function=embeddings, persist_directory=db_path)
llm = ChatGroq(model=chat_model, temperature=0, max_retries=1)
chain = prompt | llm.with_structured_output(Answer)


def call_llm(context, question):
    # free tier has a per minute limit, so wait and try again
    for attempt in range(4):
        try:
            return chain.invoke({"context": context, "question": question})
        except Exception as e:
            rate_limited = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
            if not rate_limited or attempt == 3:
                raise
            print("rate limit hit, waiting 20s")
            time.sleep(20)


def normalize(text):
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def quote_in(quote, text):
    quote, text = normalize(quote), normalize(text)
    if not quote:
        return False
    if quote in text:
        return True
    # small differences like a dropped word are ok, a made up quote is not
    blocks = SequenceMatcher(None, quote, text, autojunk=False).get_matching_blocks()
    return sum(b.size for b in blocks if b.size >= 4) / len(quote) >= 0.85


def ask(question):
    results = db.similarity_search_with_relevance_scores(question, k=top_k)
    sources = [
        {"page": doc.metadata["page"], "section": doc.metadata["section"], "score": round(score, 3), "text": doc.page_content}
        for doc, score in results
    ]
    result = {"question": question, "answer": not_found, "found": False, "citations": [], "sources": sources}

    if not sources or sources[0]["score"] < min_score:
        result["reason"] = f"best match score {sources[0]['score'] if sources else 0} is below {min_score}"
        return result

    context = "\n\n".join(s["text"] for s in sources)
    reply = call_llm(context, question)

    # keep only citations whose quote really is in a retrieved chunk of that page
    for c in reply.citations:
        match = next((s for s in sources if s["page"] == c.page and quote_in(c.quote, s["text"])), None)
        if match and c.page not in [x["page"] for x in result["citations"]]:
            result["citations"].append({"page": c.page, "section": match["section"], "quote": c.quote})

    if not reply.found or normalize(reply.answer) == normalize(not_found):
        result["reason"] = "the manual has related text but not this answer"
    elif not result["citations"]:
        result["reason"] = "answer could not be matched to the manual text"
    else:
        result["answer"] = reply.answer
        result["found"] = True
    return result
