"""The curriculum data must be complete and correctly ordered."""
from founders_sim.learn.terms import TERMS, ORDER, TIERS
from founders_sim.learn.bash_lessons import LESSONS
from founders_sim.learn.profile import Profile
from founders_sim.learn import notebook
from founders_sim.game import quiz
from founders_sim.game.engine import example_vars
from tests.helpers import make_session, run


def test_every_term_is_complete():
    assert len(TERMS) >= 150
    for term in TERMS.values():
        assert term.definition and term.why and term.example, term.id
        assert term.tier in TIERS
        for ref in term.related + term.needs:
            assert ref in TERMS, f"{term.id} refers to unknown term {ref}"


def test_prerequisites_come_earlier_in_the_order():
    position = {term: i for i, term in enumerate(ORDER)}
    for term in TERMS.values():
        for need in term.needs:
            assert position[need] < position[term.id], f"{term.id} needs {need}, which comes later"


def test_examples_fill_in_with_company_numbers():
    s = make_session()
    values = example_vars(s.game)
    for term in TERMS.values():
        text = notebook.example_for(s, term)
        assert "{" not in text and "?" not in text.replace("?'", "").replace("?\"", "") or "?" in term.example, term.id
        for field in __import__("re").findall(r"\{(\w+)\}", term.example):
            assert field in values, f"{term.id} uses unknown placeholder {field}"


def test_required_bash_commands_have_lessons_and_man_pages():
    required = ["pwd", "ls", "cd", "cat", "less", "head", "tail", "mkdir", "touch", "cp", "mv", "rm", "echo", "redirect",
                "redirect_append", "pipe", "grep", "wc", "sort", "find", "history", "tab", "up_arrow", "man", "variables",
                "chmod", "script", "paths", "ls_flags"]
    for name in required:
        assert name in LESSONS, name
        assert LESSONS[name].tip and LESSONS[name].examples
    s = make_session()
    for name in ["ls", "grep", "agent", "pitch", "chmod", "find", "sort", "export", "bash"]:
        assert name in s.shell.manpages
        assert "NAME" in run(s, f"man {name}")


def test_learning_unlocks_prerequisites_and_writes_files():
    s = make_session(quiet=False)
    s.learn("runway")
    assert s.game.notebook[:5] == ["cash", "revenue", "costs", "burn_rate", "runway"]
    out = run(s, "ls notebook", "grep -ril 'burn' notebook | wc -l", "nb runway")
    assert "runway.md" in out and "WHAT IT IS" in out
    assert s.profile.term_status("runway") == "seen"


def test_mastery_needs_two_correct_uses():
    p = Profile()
    p.see("cac")
    assert p.term_status("cac") == "seen"
    p.credit("cac")
    assert p.term_status("cac") == "practiced"
    p.credit("cac", ok=False)
    p.credit("cac")
    assert p.term_status("cac") == "mastered"
    p.credit("ltv", ok=False)
    assert "ltv" in p.struggling()


def test_profile_survives_save_and_load():
    p = Profile()
    p.credit("mrr"); p.credit("mrr"); p.bash_use("grep"); p.did("loan_term"); p.runs = 2
    p.save()
    q = Profile.load()
    assert q.term_status("mrr") == "mastered" and q.runs == 2 and q.mechanics["loan_term"] == 1


def test_quiz_number_parsing_and_grading():
    assert quiz.parse_number("$12.5k") == 12500
    assert quiz.parse_number("8%") == 8
    assert quiz.parse_number("1.2m") == 1_200_000
    assert quiz.parse_number("7 months") == 7
    assert quiz.parse_number("lots") is None
    s = make_session(answers=["2.5m", "banana"])
    q = quiz.Question("post_money", "post?", 2_500_000, "$")
    assert quiz.ask(s, q) is True
    assert quiz.ask(s, q) is False
    assert s.profile.terms["post_money"] == {"seen": 1, "ok": 1, "bad": 1}


def test_concept_questions_reference_real_terms():
    for q in quiz.concept_questions():
        assert q.term in TERMS and len(q.options) == 4 and len(set(q.options)) == 4
    s = make_session()
    for q in quiz.calc_questions(s) + quiz.number_questions(s):
        assert q.term in TERMS


def test_glossary_and_tutor_render():
    s = make_session()
    out = run(s, "glossary", "tutor", "notebook")
    assert "Curriculum progress" in out and "Stage 6" in out and "Tutor" in out
