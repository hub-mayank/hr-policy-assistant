import os
import re
import shutil
import time

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()

pdf_path = "data/hr_manual.pdf"
db_path = "db"
collection = "hr_manual"

# cover, contents, empty divider pages and back cover have nothing to answer from
skip_pages = [1, 2, 3, 39, 66, 79]

# start pages checked by hand, the contents page in the pdf is off by a page in some places
parts = [
    (4, "Introduction"),
    (5, "Section I - Employing Staff"),
    (16, "Section II - Managing Employee Performance"),
    (22, "Section III - Dealing with Employee Concerns"),
    (28, "Section IV - Supporting Our Staff in the Workplace"),
    (34, "Company Rules & Regulations"),
    (39, "Annexure I"),
    (48, "Annexure II"),
    (52, "Annexure III"),
    (66, "Annexure IV - Traveling Policies"),
]

# (first page, last page, policy), a page can belong to two policies
policies = [
    (6, 6, "1.1 Recruitment"),
    (6, 8, "1.2 Induction Policy"),
    (8, 9, "1.3 Employee's Employment"),
    (9, 11, "1.4 Standards of Business Conduct"),
    (12, 15, "1.5 Internet and Email Usage Policy"),
    (17, 18, "2.1 Performance Appraisal Policy"),
    (18, 19, "2.2 Controlling Absence Policy"),
    (19, 21, "2.3 Disciplinary Procedure"),
    (21, 21, "2.4 Capability Procedure"),
    (23, 23, "3.1 Grievance Procedure"),
    (24, 25, "3.2 Prevention of Bullying and Harassment at Work"),
    (26, 27, "3.3 Whistleblowing Policy"),
    (29, 30, "4.1 Equality Policy"),
    (31, 31, "4.2 Drug and Alcohol Abuse Policy"),
    (31, 33, "4.3 Health and Safety Policy"),
    (34, 34, "Staff Handbook and Company Property"),
    (35, 35, "IT Security, Personal Mail & Calls Policy"),
    (36, 36, "Non-Disclosure of Confidential Information"),
    (37, 38, "Conflict of Interest"),
    (40, 41, "a. On Boarding Process"),
    (42, 43, "b. Probation Policy"),
    (44, 44, "c. Training and Development"),
    (45, 45, "d. Relocation Policy"),
    (46, 47, "e. Off-Boarding Process"),
    (49, 50, "a. Equal Opportunities"),
    (51, 51, "b. Data Card / Visiting Cards / Emails Policy"),
    (53, 53, "a. Dress Code"),
    (54, 54, "b. Work Timing Policy"),
    (55, 56, "c. Punctuality and Attendance"),
    (57, 57, "d. Compensation Policy"),
    (58, 58, "e. Staff Advances"),
    (59, 59, "f. Employment of Relatives Policy"),
    (60, 62, "g. Leave Policy"),
    (63, 63, "h. Reward & Recognition"),
    (64, 65, "i. Whistle Blower Policy & Anti Sexual Harassment Policy"),
    (67, 72, "a. Long Distance Travel Policy"),
    (73, 78, "b. Short Distance Travel Policy"),
]


def get_section(page):
    part = ""
    for start, name in parts:
        if start <= page:
            part = name
    names = [name for first, last, name in policies if first <= page <= last]
    if names:
        return part + " > " + " / ".join(names)
    return part


def clean(text):
    text = re.sub(r"^HR Manual - \d+\s*", "", text)
    # the pdf uses odd glyphs for bullets
    text = re.sub(r"[Ԃ▶¤•»-]", "-", text)
    # join words broken across lines like "al -\nlowed"
    text = re.sub(r"(\w) ?- ?\n(\w)", r"\1\2", text)
    # "12 weeks( -\n90days)" -> "12 weeks (90days)"
    text = re.sub(r"\(\s*-\s*", " (", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n\s*", "\n", text)
    # table cells come out as short lines, keep a line break only before bullets and numbered points
    text = re.sub(r"\n(?!-|\d+\.\s)", " ", text)
    return text.strip()


def main():
    pages = PyPDFLoader(pdf_path).load()
    print(f"loaded {len(pages)} pages")

    docs = []
    for doc in pages:
        page = doc.metadata["page"] + 1
        if page in skip_pages:
            continue
        doc.page_content = clean(doc.page_content)
        doc.metadata = {"page": page, "section": get_section(page)}
        docs.append(doc)

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(docs)

    # put the section name on top of every chunk, helps retrieval and gives the llm the reference
    for chunk in chunks:
        chunk.page_content = f"[{chunk.metadata['section']} | page {chunk.metadata['page']}]\n{chunk.page_content}"

    print(f"made {len(chunks)} chunks from {len(docs)} pages")

    # fresh db every time so running ingest twice doesn't add duplicates
    if os.path.exists(db_path):
        shutil.rmtree(db_path)

    embeddings = GoogleGenerativeAIEmbeddings(model=os.getenv("EMBED_MODEL", "gemini-embedding-001"))
    db = Chroma(
        collection_name=collection,
        embedding_function=embeddings,
        persist_directory=db_path,
        collection_configuration={"hnsw": {"space": "cosine"}},
    )

    batch_size = 40
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        while True:
            try:
                db.add_documents(batch)
                break
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    print("rate limit hit, waiting 30s")
                    time.sleep(30)
                else:
                    raise
        print(f"stored {min(i + batch_size, len(chunks))}/{len(chunks)}")

    print("ingest done")


if __name__ == "__main__":
    main()
