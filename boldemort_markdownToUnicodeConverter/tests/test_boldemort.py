"""Tests for boldemort.py — Markdown to Unicode converter."""

import subprocess
import sys
import tempfile
from pathlib import Path

# Adjust path so we can import the top-level module directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

from boldemort import convert, _strike  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCRIPT = str(Path(__file__).parent.parent / "boldemort.py")


def run_cli(*args: str, stdin: str = "") -> tuple[int, str, str]:
    """Run the boldemort CLI and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, SCRIPT, *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# Bold (**text** and __text__)
# ---------------------------------------------------------------------------


class TestBold:
    def test_double_asterisk_basic(self) -> None:
        out = convert("**Hello**")
        assert out != "**Hello**"
        assert "H" not in out and "e" not in out  # translated
        assert "**" not in out

    def test_double_asterisk_uppercase(self) -> None:
        out = convert("**ABC**")
        assert out == "𝗔𝗕𝗖"

    def test_double_asterisk_lowercase(self) -> None:
        out = convert("**abc**")
        assert out == "𝗮𝗯𝗰"

    def test_double_asterisk_digits(self) -> None:
        out = convert("**123**")
        assert out == "𝟭𝟮𝟯"

    def test_double_asterisk_mixed(self) -> None:
        out = convert("**Hello World**")
        assert out == "𝗛𝗲𝗹𝗹𝗼 𝗪𝗼𝗿𝗹𝗱"

    def test_double_underscore_basic(self) -> None:
        out = convert("__Hello__")
        assert out == "𝗛𝗲𝗹𝗹𝗼"

    def test_double_underscore_uppercase(self) -> None:
        out = convert("__ABC__")
        assert out == "𝗔𝗕𝗖"

    def test_double_underscore_lowercase(self) -> None:
        out = convert("__abc__")
        assert out == "𝗮𝗯𝗰"

    def test_bold_in_sentence(self) -> None:
        out = convert("This is **important** text.")
        assert out == "This is 𝗶𝗺𝗽𝗼𝗿𝘁𝗮𝗻𝘁 text."

    def test_multiple_bold_spans(self) -> None:
        out = convert("**a** and **b**")
        assert out == "𝗮 and 𝗯"

    def test_bold_no_newline_crossing(self) -> None:
        out = convert("**line1\nline2**")
        assert out == "**line1\nline2**"


# ---------------------------------------------------------------------------
# Italic (*text* and _text_)
# ---------------------------------------------------------------------------


class TestItalic:
    def test_single_asterisk_basic(self) -> None:
        out = convert("*Hello*")
        assert out == "𝘏𝘦𝘭𝘭𝘰"

    def test_single_asterisk_uppercase(self) -> None:
        out = convert("*ABC*")
        assert out == "𝘈𝘉𝘊"

    def test_single_asterisk_lowercase(self) -> None:
        out = convert("*abc*")
        assert out == "𝘢𝘣𝘤"

    def test_single_underscore_basic(self) -> None:
        out = convert("_Hello_")
        assert out == "𝘏𝘦𝘭𝘭𝘰"

    def test_italic_in_sentence(self) -> None:
        out = convert("Some *emphasis* here.")
        assert out == "Some 𝘦𝘮𝘱𝘩𝘢𝘴𝘪𝘴 here."

    def test_italic_no_newline_crossing(self) -> None:
        out = convert("*line1\nline2*")
        assert out == "*line1\nline2*"

    def test_multiple_italic_spans(self) -> None:
        out = convert("*a* and *b*")
        assert out == "𝘢 and 𝘣"


# ---------------------------------------------------------------------------
# Monospace (`text`)
# ---------------------------------------------------------------------------


class TestMono:
    def test_backtick_basic(self) -> None:
        out = convert("`Hello`")
        assert out == "𝙷𝚎𝚕𝚕𝚘"

    def test_backtick_uppercase(self) -> None:
        out = convert("`ABC`")
        assert out == "𝙰𝙱𝙲"

    def test_backtick_lowercase(self) -> None:
        out = convert("`abc`")
        assert out == "𝚊𝚋𝚌"

    def test_backtick_digits(self) -> None:
        out = convert("`123`")
        assert out == "𝟷𝟸𝟹"

    def test_backtick_in_sentence(self) -> None:
        out = convert("Run `ls -la` now.")
        assert out == "Run 𝚕𝚜 -𝚕𝚊 now."

    def test_backtick_no_newline_crossing(self) -> None:
        out = convert("`line1\nline2`")
        assert out == "`line1\nline2`"

    def test_multiple_mono_spans(self) -> None:
        out = convert("`a` and `b`")
        assert out == "𝚊 and 𝚋"


# ---------------------------------------------------------------------------
# Strikethrough (~~text~~)
# ---------------------------------------------------------------------------


class TestStrikethrough:
    def test_basic(self) -> None:
        out = convert("~~gone~~")
        # Each character should be followed by the combining stroke
        assert "̶" in out
        assert "~~" not in out

    def test_every_char_has_combining(self) -> None:
        out = convert("~~abc~~")
        chars = list(out)
        # Pairs: a, ̶, b, ̶, c, ̶
        for i, ch in enumerate("abc"):
            assert chars[i * 2] == ch
            assert chars[i * 2 + 1] == "̶"

    def test_strike_helper(self) -> None:
        result = _strike("hi")
        assert result == "h̶i̶"

    def test_strike_in_sentence(self) -> None:
        out = convert("This is ~~deleted~~ text.")
        assert "~~" not in out
        assert "̶" in out
        assert out.startswith("This is ")
        assert out.endswith(" text.")


# ---------------------------------------------------------------------------
# Passthrough — non-matching text must be unchanged
# ---------------------------------------------------------------------------


class TestPassthrough:
    def test_plain_text(self) -> None:
        assert convert("Hello, world!") == "Hello, world!"

    def test_empty_string(self) -> None:
        assert convert("") == ""

    def test_multiline_plain(self) -> None:
        text = "line one\nline two\nline three"
        assert convert(text) == text

    def test_special_chars_unchanged(self) -> None:
        text = "Price: $100 & 20% off"
        assert convert(text) == text

    def test_single_asterisk_no_close(self) -> None:
        assert convert("dangling *asterisk") == "dangling *asterisk"

    def test_double_asterisk_no_close(self) -> None:
        assert convert("dangling **asterisk") == "dangling **asterisk"

    def test_backtick_no_close(self) -> None:
        assert convert("dangling `backtick") == "dangling `backtick"


# ---------------------------------------------------------------------------
# Precedence: backtick content is not further substituted
# ---------------------------------------------------------------------------


class TestPrecedence:
    def test_mono_protects_bold_markers(self) -> None:
        # **text** inside backticks must NOT become bold
        out = convert("`**not bold**`")
        # Should be monospace, not bold
        assert "𝟎" not in out  # no bold digits
        assert "**" not in out  # markers consumed by mono

    def test_bold_before_italic(self) -> None:
        # **text** should win over *text* overlap situations
        out = convert("**bold** and *italic*")
        assert "𝗯𝗼𝗹𝗱" in out
        assert "𝘪𝘵𝘢𝘭𝘪𝘤" in out


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestCLI:
    def test_stdin_stdout(self) -> None:
        code, out, err = run_cli(stdin="**bold**")
        assert code == 0
        assert out == "𝗯𝗼𝗹𝗱"
        assert err == ""

    def test_stdin_italic(self) -> None:
        code, out, _ = run_cli(stdin="*italic*")
        assert code == 0
        assert out == "𝘪𝘵𝘢𝘭𝘪𝘤"

    def test_file_input_stdout(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write("**file bold**")
            fname = f.name
        code, out, _ = run_cli(fname)
        assert code == 0
        assert out == "𝗳𝗶𝗹𝗲 𝗯𝗼𝗹𝗱"
        Path(fname).unlink()

    def test_file_input_file_output(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fin:
            fin.write("`code`")
            in_name = fin.name
        with tempfile.NamedTemporaryFile(
            suffix=".txt", delete=False
        ) as fout:
            out_name = fout.name

        code, _, _ = run_cli(in_name, "-o", out_name)
        assert code == 0
        result = Path(out_name).read_text(encoding="utf-8")
        assert result == "𝚌𝚘𝚍𝚎"
        Path(in_name).unlink()
        Path(out_name).unlink()

    def test_passthrough_plain(self) -> None:
        code, out, _ = run_cli(stdin="plain text")
        assert code == 0
        assert out == "plain text"

    def test_multiline_input(self) -> None:
        inp = "**bold**\n*italic*\n`mono`"
        code, out, _ = run_cli(stdin=inp)
        assert code == 0
        lines = out.split("\n")
        assert lines[0] == "𝗯𝗼𝗹𝗱"
        assert lines[1] == "𝘪𝘵𝘢𝘭𝘪𝘤"
        assert lines[2] == "𝚖𝚘𝚗𝚘"
