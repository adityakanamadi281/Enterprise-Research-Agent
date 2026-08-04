from app.services.research import abstract


def test_inverted_openalex_abstract_is_reconstructed() -> None:
    assert abstract({"AI": [1], "manufacturing": [2], "in": [0]}) == "in AI manufacturing"


def test_missing_abstract_is_explicit() -> None:
    assert "No abstract" in abstract(None)


def test_end_to_end_research_session() -> None:
    from app.domain.models import SessionLocal, RunEvent
    from app.services.research import run_research

    db = SessionLocal()
    try:
        session = run_research(db, "What are recent developments in quantum error correction?")
        if session.status != "completed":
            events = db.query(RunEvent).filter(RunEvent.research_session_id == session.id).all()
            print("RUN EVENTS:", [(e.step, e.status, e.details) for e in events])
        assert session.status == "completed"
        assert session.conclusion is not None
        assert session.confidence > 0
    finally:
        db.close()


