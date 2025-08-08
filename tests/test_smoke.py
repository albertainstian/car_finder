import importlib, pathlib
def test_import(): importlib.import_module("carfinder")
def test_readme(): assert pathlib.Path("README.md").exists()
