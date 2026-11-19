from src.services.context_manager import ContextManager


def test_context_preserved():
    context = ContextManager(max_messages=3)
    context.add(7, "user", "أول سؤال")
    context.add(7, "assistant", "أول جواب")
    context.add(7, "user", "ثاني سؤال")
    history = context.get(7)
    assert len(history) == 3
    assert history[-1]["content"] == "ثاني سؤال"
