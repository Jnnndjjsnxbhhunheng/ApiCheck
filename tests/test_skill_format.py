"""
Validate that api-detect/SKILL.md has the correct structure:
- Valid YAML frontmatter with required fields
- Non-empty workflow content
"""

import re
import os

SKILL_PATH = os.path.join(os.path.dirname(__file__), "..", ".claude", "skills", "api-detect", "SKILL.md")


def read_skill():
    with open(SKILL_PATH, encoding="utf-8") as f:
        return f.read()


def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter between --- delimiters."""
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, "SKILL.md must start with --- frontmatter ---"
    import yaml
    return yaml.safe_load(match.group(1))


def test_frontmatter_exists():
    text = read_skill()
    assert text.startswith("---"), "SKILL.md must start with YAML frontmatter"


def test_frontmatter_has_name():
    text = read_skill()
    fm = parse_frontmatter(text)
    assert "name" in fm, "frontmatter must have 'name'"
    assert fm["name"] == "api-detect"


def test_frontmatter_has_description():
    text = read_skill()
    fm = parse_frontmatter(text)
    assert "description" in fm, "frontmatter must have 'description'"
    assert len(str(fm["description"]).strip()) > 20, "description must be non-trivial"


def test_frontmatter_description_has_trigger():
    text = read_skill()
    fm = parse_frontmatter(text)
    desc = str(fm["description"])
    assert "TRIGGER" in desc, "description should contain TRIGGER conditions"
    assert "DO NOT TRIGGER" in desc, "description should contain DO NOT TRIGGER guard"


def test_workflow_content_exists():
    text = read_skill()
    body = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    assert len(body.strip()) > 200, "SKILL.md body (workflow) must not be empty"


def test_workflow_has_wrap_up():
    text = read_skill()
    assert "Wrap up" in text or "wrap up" in text.lower(), \
        "SKILL.md should have a 'Wrap up' section defining the output format"
