import importlib, pathlib
def test_import(): importlib.import_module("car_finder")
def test_readme(): assert pathlib.Path("README.md").exists()
