import importlib


def test_imports():
    # Core modules import
    assert importlib.import_module("aiwand.app")
    assert importlib.import_module("aiwand.config")
    # UI widgets module
    assert importlib.import_module("aiwand.ui.widgets")
