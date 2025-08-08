import importlib, pathlib
def test_import(): assert importlib.import_module("car_finder")
def test_readme_exists(): assert pathlib.Path("README.md").exists()
