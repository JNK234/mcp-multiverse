# ABOUTME: Tests for the frontmatter codec — split/join '---\nYAML\n---\nbody' for SKILL.md.
# ABOUTME: Written test-first. Body is preserved byte-exact; no-frontmatter case returns {}.
from mcpx.codecs.frontmatter import join, split


def test_split_basic() -> None:
    text = "---\nname: x\ndescription: hi\n---\nBody line 1\nBody line 2\n"
    fm, body = split(text)
    assert fm == {"name": "x", "description": "hi"}
    assert body == "Body line 1\nBody line 2\n"


def test_split_no_frontmatter_returns_empty_and_full_body() -> None:
    text = "Just a body, no frontmatter at all.\nSecond line.\n"
    fm, body = split(text)
    assert fm == {}
    assert body == text


def test_split_preserves_extra_keys() -> None:
    text = (
        "---\nname: kw\ndescription: d\n"
        "argument-hint: '[topic]'\ndisable-model-invocation: true\n---\nbody\n"
    )
    fm, body = split(text)
    assert fm["name"] == "kw"
    assert fm["argument-hint"] == "[topic]"
    assert fm["disable-model-invocation"] is True


def test_split_list_valued_key() -> None:
    text = "---\nname: x\nallowed-tools:\n  - Bash\n  - Read\n---\nbody\n"
    fm, _ = split(text)
    assert fm["allowed-tools"] == ["Bash", "Read"]


def test_split_multiline_description() -> None:
    text = (
        "---\n"
        "name: x\n"
        "description: >\n"
        "  line one\n"
        "  line two\n"
        "---\n"
        "body\n"
    )
    fm, _ = split(text)
    assert "line one" in fm["description"]
    assert "line two" in fm["description"]


def test_split_body_is_byte_exact() -> None:
    """Body must survive verbatim — exotic whitespace, code fences, trailing newlines."""
    body = "# Title\n\n```python\nx = 1  # trailing spaces   \n```\n\n- item\n\n\n"
    text = f"---\nname: x\n---\n{body}"
    _, out = split(text)
    assert out == body


def test_join_roundtrip() -> None:
    fm = {"name": "x", "description": "hi"}
    body = "Body here.\n"
    text = join(fm, body)
    fm2, body2 = split(text)
    assert fm2 == fm
    assert body2 == body


def test_join_empty_frontmatter_writes_body_only() -> None:
    text = join({}, "just body\n")
    assert text == "just body\n"
    assert "---" not in text
