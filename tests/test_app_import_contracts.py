import ast
import importlib
from pathlib import Path


def test_all_src_imports_used_by_app_exist():
    """Catch broken app.py imports before Streamlit deploys them.

    The production app imports a large number of feature modules at startup. A
    missing renamed symbol otherwise crashes the entire app before Streamlit can
    render any fallback UI.
    """
    root = Path(__file__).resolve().parents[1]
    source = (root / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    checked = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        module_name = node.module or ""
        if not module_name.startswith("src."):
            continue
        module = importlib.import_module(module_name)
        for alias in node.names:
            if alias.name == "*":
                continue
            assert hasattr(module, alias.name), (
                f"app.py imports {alias.name!r} from {module_name!r}, "
                "but that symbol does not exist"
            )
            checked.append((module_name, alias.name))

    assert checked, "No src imports were checked; app.py structure may have changed"
