import sys
import time

from rag import ask, not_found

exam_questions = [
    "How many days of Privilege Leave (PL) does a permanent employee get per year?",
    "What is the probation period for employees up to Senior Manager?",
    "What is the company's health-insurance premium amount?",
    "What is the current GST rate in India?",
    "How many days of maternity leave are given?",
]

# (question, word that must be in the answer, pages it can come from), None means it should be Not found
tests = [
    (exam_questions[0], "12", [60]),
    (exam_questions[1], "3 months", [42]),
    (exam_questions[2], None, None),
    (exam_questions[3], None, None),
    (exam_questions[4], "90", [62]),
    ("How many days of sick leave does an employee get?", "6", [60, 61]),
    ("Can unused Privilege Leave be carried forward to the next year?", "not", [60]),
    ("How much leave is given in case of a miscarriage?", "four weeks", [62]),
    ("How many times can the probation period be extended?", "one", [42]),
    ("What is the notice period for resignation?", "30", [46]),
    ("Is smoking allowed inside company buildings?", "no", [32, 35]),
    ("Who is the CEO of Enso Group?", None, None),
    ("What is the gratuity amount after 5 years of service?", None, None),
    ("What percentage of salary goes to PF?", None, None),
    ("How many days of paternity leave are given?", None, None),
    ("What is the capital of France?", None, None),
]


def show(result):
    print(f"\nQ: {result['question']}")
    print(f"A: {result['answer']}")
    for c in result["citations"]:
        print(f"   reference: {c['section']}, page {c['page']}")
        print(f"   quote: \"{c['quote']}\"")
    if "reason" in result:
        print(f"   why: {result['reason']}")
    print(f"   top match: page {result['sources'][0]['page']} (score {result['sources'][0]['score']})")


def run_tests():
    passed = 0
    rows = []
    for question, word, pages in tests:
        result = ask(question)
        cited = [c["page"] for c in result["citations"]]
        if word is None:
            ok = result["answer"] == not_found
        else:
            ok = result["found"] and word in result["answer"].lower() and any(p in pages for p in cited)
        passed += ok
        expected = not_found if word is None else f"'{word}' from page {pages}"
        rows.append((ok, question, expected, result["answer"], cited))
        show(result)
        # stay under the free tier tokens per minute limit
        time.sleep(12)

    print("\n" + "-" * 80)
    for ok, question, expected, answer, cited in rows:
        print(f"{'PASS' if ok else 'FAIL'}  {question}")
        print(f"      expected: {expected} | got: {answer[:70]} | pages: {cited}")
    print(f"\n{passed}/{len(tests)} passed")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_tests()
    elif len(sys.argv) > 1:
        show(ask(" ".join(sys.argv[1:])))
    else:
        for question in exam_questions:
            show(ask(question))
