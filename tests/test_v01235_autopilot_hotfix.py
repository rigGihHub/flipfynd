import re
from pathlib import Path


def test_app_uses_compat_wrapper():
    app = Path("app.py").read_text(encoding="utf-8")
    assert "build_autopilot_plan_compat(" in app

    match = re.search(r'APP_VERSION = "v(\d+)\.(\d+)\.(\d+)"', app)
    assert match, "app.py ska deklarera APP_VERSION"
    version = tuple(int(part) for part in match.groups())
    assert version >= (0, 12, 80)
