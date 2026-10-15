"""C2/C5 structural purity guard (08 section 3.1), by AST: the source is parsed, never imported.

These prove SHAPE: `classify` cannot take history or state, and the classifier package cannot reach
the engine, generation, orchestrator or the web stack. The request-level C2/C5 tests in
tests/test_tutor_message.py prove BEHAVIOUR; they are not duplicates.
"""

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
CLASSIFIER = APP / "classifier"
FORBIDDEN_APP = ("app.escalation", "app.generation", "app.main", "app.orchestrator")
FORBIDDEN_THIRD_PARTY = ("fastapi", "httpx", "starlette", "requests")


def _under(name: str, prefixes) -> bool:
    return any(name == p or name.startswith(p + ".") for p in prefixes)


def _imports_of_source(source: str, package: list[str]) -> list[str]:
    """Absolute dotted names imported by a module whose package is `package` (relative imports resolved)."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: len(package) - (node.level - 1)]
                module = ".".join(base + ([node.module] if node.module else []))
            else:
                module = node.module or ""
            found.append(module)
            found += [f"{module}.{a.name}" for a in node.names if a.name != "*"]
    return found


def _imports(path: Path) -> list[str]:
    package = list(path.relative_to(APP.parent).with_suffix("").parts[:-1])  # ['app', 'classifier']
    return _imports_of_source(path.read_text(encoding="utf-8"), package)


def test_classify_takes_exactly_model_and_text():
    tree = ast.parse((CLASSIFIER / "hybrid.py").read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "classify")
    a = fn.args
    assert [p.arg for p in a.posonlyargs + a.args] == ["model", "text"]
    assert not a.defaults and not a.kw_defaults
    assert a.vararg is None and a.kwarg is None and not a.kwonlyargs


def test_classifier_package_imports_nothing_it_must_not():
    files = sorted(CLASSIFIER.rglob("*.py"))
    assert files
    bad = []
    for path in files:
        for name in _imports(path):
            if _under(name, FORBIDDEN_APP) or _under(name, FORBIDDEN_THIRD_PARTY):
                bad.append(f"{path.name}: {name}")
    assert not bad, bad


def test_the_import_resolver_sees_relative_and_absolute_forbidden_imports():
    """A negative control for the guard itself."""
    names = _imports_of_source(
        "from ..escalation import engine\nimport httpx\nfrom app import generation\n", ["app", "classifier"]
    )
    assert any(_under(n, FORBIDDEN_APP) for n in names)
    assert "httpx" in names
    assert "app.generation" in names
