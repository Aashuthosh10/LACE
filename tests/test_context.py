from pathlib import Path

import pytest

from lace.config import RepositoryLimits
from lace.context import select_context
from lace.repository import scan_repository
from lace.repository.models import RepositoryScanError


def test_ranks_filename_symbols_and_keywords(scanning_repository: Path) -> None:
    inventory = scan_repository(scanning_repository)
    result = select_context(inventory, "Fix incorrect discount calculation")
    assert result.files[0].path == "src/shop/discount.py"
    assert result.files[0].score > result.files[1].score
    assert any(reason.startswith("filename: discount") for reason in result.files[0].reasons)
    assert any(reason.startswith("python symbols:") for reason in result.files[0].reasons)
    assert "### src/shop/discount.py" in result.context


def test_selection_is_deterministic(scanning_repository: Path) -> None:
    inventory = scan_repository(scanning_repository)
    first = select_context(inventory, "discount calculator")
    second = select_context(inventory, "discount calculator")
    assert first == second


def test_enforces_context_and_selected_file_budgets(scanning_repository: Path) -> None:
    inventory = scan_repository(scanning_repository)
    one_file = select_context(
        inventory,
        "discount",
        RepositoryLimits(max_selected_files=1, max_context_chars=10_000),
    )
    assert len(one_file.files) == 1
    assert "selected-file limit reached" in one_file.warnings

    no_room = select_context(
        inventory,
        "discount",
        RepositoryLimits(max_context_chars=10),
    )
    assert no_room.files == ()
    assert no_room.context_chars == 0
    assert any("context budget" in warning for warning in no_room.warnings)


def test_missing_match_and_invalid_task(scanning_repository: Path) -> None:
    inventory = scan_repository(scanning_repository)
    result = select_context(inventory, "frobnicate quux")
    assert result.files == ()
    assert "no relevant Python files matched the task" in result.warnings
    with pytest.raises(ValueError, match="meaningful word"):
        select_context(inventory, "the and to")


def test_rejects_file_changed_after_inventory(scanning_repository: Path) -> None:
    inventory = scan_repository(scanning_repository)
    (scanning_repository / "src" / "shop" / "discount.py").write_text(
        "changed = True\n", encoding="utf-8"
    )
    with pytest.raises(RepositoryScanError, match="changed during context selection"):
        select_context(inventory, "discount")
