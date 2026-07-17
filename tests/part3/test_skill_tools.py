"""Tests for Part 3 skill_tools."""

from pathlib import Path

from part3_agent.skill_tools import (
    SKILLS_DIR,
    LOG_INDEX_CATALOG_PATH,
    format_log_index_catalog_for_product,
    list_skills,
    load_log_index_catalog,
    load_skill_content,
)

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "part3_agent" / "skills"


def test_list_skills_returns_catalog() -> None:
    catalog = list_skills(skills_dir=FIXTURES_DIR)
    names = {item["name"] for item in catalog}
    assert "troubleshoot" in names
    assert "troubleshoot-apm-incidents" in names
    assert all("description" in item for item in catalog)


def test_load_skill_content_by_directory() -> None:
    content = load_skill_content("troubleshoot-apm-incidents", skills_dir=FIXTURES_DIR)
    assert content is not None
    assert "troubleshoot-apm-incidents" in content


def test_load_skill_content_include_reference() -> None:
    content = load_skill_content(
        "troubleshoot",
        skills_dir=FIXTURES_DIR,
        include_reference=True,
    )
    assert content is not None
    assert "reference" in content.lower()


def test_load_skill_content_unknown_returns_none() -> None:
    assert load_skill_content("nonexistent-skill", skills_dir=SKILLS_DIR) is None


def test_load_log_index_catalog_parses_frontmatter() -> None:
    catalog = load_log_index_catalog(catalog_path=LOG_INDEX_CATALOG_PATH)
    assert catalog is not None
    assert catalog.get("tenant") == "o11y-workshop-amer"
    assert catalog.get("default_index") == "splunk4rookies-workshop"
    products = catalog.get("products")
    assert isinstance(products, dict)
    assert "apm" in products


def test_format_log_index_catalog_for_apm() -> None:
    text = format_log_index_catalog_for_product(
        "apm",
        service_name="Verification",
    )
    assert "splunk4rookies-workshop" in text
    assert "kube:container:verification" in text
    assert "_internal" in text
    assert "do not search" in text


def test_format_log_index_catalog_unknown_product_uses_defaults() -> None:
    catalog = load_log_index_catalog(catalog_path=LOG_INDEX_CATALOG_PATH)
    text = format_log_index_catalog_for_product("unknown", catalog=catalog)
    assert "splunk4rookies-workshop" in text or text == ""
