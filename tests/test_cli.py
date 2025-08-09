import subprocess, sys, pathlib

def test_readme_exists():
    assert pathlib.Path("README.md").exists()

def test_cli_help_runs():
    p = subprocess.run([sys.executable, "carfind.py", "--help"],
                       capture_output=True, text=True)
    assert p.returncode == 0
    assert "--query" in p.stdout and "--regions" in p.stdout
