"""check_llm.py — verify CLI-backed LLMs are installed, authenticated, and resumable."""

from llms import Claude, Codex, Gemini, ToolMode

PING = "Reply with exactly: OK"
CODEWORD = "CHECK-LLM-42"

checks = [
    Codex(),
    Gemini(),
    Claude(),
]


def preview(text: str, limit: int = 80) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return repr(text)
    return repr(text[: limit - 1] + "…")


def check_direct(llm) -> tuple[bool, str]:
    response = llm.ask(PING)
    ok = response.text.strip() == "OK"
    detail = f"ask={preview(response.text)}"
    if not ok:
        detail += " expected='OK'"
    return ok, detail


def check_session(llm) -> tuple[bool, str]:
    first = llm.start(
        f"Remember this codeword: {CODEWORD}. Reply with exactly: OK",
        ToolMode.READ_ONLY,
    )
    if first.text.strip() != "OK":
        return False, f"start={preview(first.text)} expected='OK'"
    session = llm.make_session(first, ToolMode.READ_ONLY)
    second = llm.send(
        session,
        "What is the codeword? Reply with only the codeword.",
    )
    ok = second.text.strip() == CODEWORD
    detail = f"session={second.session_id} resume={preview(second.text)}"
    if not ok:
        detail += f" expected={CODEWORD!r}"
    return ok, detail


def main() -> int:
    print("\n  LLM Health Check")
    print("  " + "-" * 76)

    failures = 0
    for llm in checks:
        details: list[str] = []
        try:
            direct_ok, direct_detail = check_direct(llm)
            session_ok, session_detail = check_session(llm)
            details.extend([direct_detail, session_detail])
            status = "ready" if direct_ok and session_ok else "failed"
        except Exception as e:
            status = "failed"
            details.append(f"{type(e).__name__}: {e}")

        if status != "ready":
            failures += 1
        marker = "OK" if status == "ready" else "FAIL"
        print(f"  {llm.name:<30} {marker:<5} {status}")
        for detail in details:
            print(f"  {'':30} {detail}")
        print()

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
