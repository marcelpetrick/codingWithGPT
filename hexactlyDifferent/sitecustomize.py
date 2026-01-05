import os

if os.environ.get("COVERAGE_PROCESS_START"):
    try:
        import coverage
        coverage.process_startup()
    except Exception:
        # Avoid breaking normal runs if coverage is unavailable
        pass
