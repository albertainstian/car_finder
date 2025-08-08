import importlib, pathlib
def test_import():
    for name in ("carfinder", "car_finder"):
        try:
            importlib.import_module(name)
            return
        except Exception:
            pass
    raise AssertionError("Could not import carfinder or car_finder")
def test_readme():
    assert pathlib.Path("README.md").exists()
