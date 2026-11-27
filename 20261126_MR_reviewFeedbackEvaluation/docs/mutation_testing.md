# Mutation testing

Run: `./localPipeline.sh` (stage "mutation testing", gate: score at least 80%), or `uv run mutmut run` and `uv run mutmut results`.
Scope: `bizhours.py`, `textutil.py`, `evaluate.py`, `evidence.py` (the modules with the most decision logic), against the unit tests.
The other modules are covered by integration and browser tests, which mutmut does not run here.

## Round 1 (2026-11-26, mutmut 3.8.1)

| Result | Count |
|---|---|
| Mutants | 709 |
| Killed | 471 |
| Survived | 94 |
| No unit test reaches the code (integration-tested paths) | 144 |
| Score over reached mutants | 471 / 565 = 83.4% |

Surviving mutants, by kind:

| Kind | Verdict | Action |
|---|---|---|
| SQL keywords in lower case | Equivalent: SQL keywords ignore case | none |
| `row["CREATED_AT"]` instead of `row["created_at"]` | Equivalent: `sqlite3.Row` keys ignore case | none |
| `hi >= lo` instead of `hi > lo` | Equivalent: adds zero seconds | none |
| Changed error message text (`"XX…XX"`) | Equivalent for behaviour: tests match a substring | none |
| `"+1"` replacement removed | Equivalent: `+1` is also in the routine word list | none |
| Character categories in `_is_decoration` | Mostly equivalent for the tested inputs; low risk | none |
| `astimezone(None)` in `BusinessCalendar.seconds` | **Missing assertion**: tests passed only because this machine runs in Europe/Berlin | test with Pacific/Auckland |
| `start_hour <= end_hour` allowed | **Missing assertion** | test for equal hours |
| Censoring boundary `<` instead of `<=` | **Missing assertion** | boundary test |
| `truncate` limit `<= 1` | **Missing assertion** | limit-1 test |
| Routine word limit `>=` | **Missing assertion** | 8 and 9 word test |
| Rounding precision removed in `_span` | **Missing assertion** | fractional test |

The new tests are in `tests/unit/test_mutation_gaps.py`.

## Round 1b, after the new tests

| Result | Count |
|---|---|
| Killed | 487 |
| Survived | 78 (equivalent kinds above) |
| Score over reached mutants | 487 / 565 = 86.2% |

## Round 2 (2026-11-26, after the compare-API evidence stage)

| Result | Count |
|---|---|
| Mutants | 730 |
| Killed | 626 |
| Score over reached mutants (the gate value) | 626 / 730 = 85.8% |

The gate first failed at 77.8%: the new compare branch in `evaluate.py` had only integration tests.
Unit tests for every branch (`test_compare_evidence_branches` and two more) brought it to 85.8%.

## Round 3 (2026-11-27, v0.3.x)

| Result | Count |
|---|---|
| Killed | 646 |
| Survived | 104 |
| Score over reached mutants (the gate value) | 646 / 750 = 86.1% |
