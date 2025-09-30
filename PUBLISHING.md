# Publishing ReachGenie to PyPI

This guide explains how to publish ReachGenie to the Python Package Index (PyPI).

## Prerequisites

1. **Create PyPI Account:**
   - Go to https://pypi.org/account/register/
   - Create an account and verify your email

2. **Create API Token:**
   - Go to https://pypi.org/manage/account/token/
   - Create a new API token
   - Save it securely (you'll only see it once)

3. **Install build tools:**
```bash
pip install --upgrade build twine
```

## Publishing Steps

### 1. Update Version

Update the version in both files:
- `setup.py` (line with `version="x.x.x"`)
- `pyproject.toml` (line with `version = "x.x.x"`)
- `src/__init__.py` (line with `__version__ = "x.x.x"`)

### 2. Clean Previous Builds

```bash
rm -rf dist/ build/ *.egg-info
```

### 3. Build the Package

```bash
python -m build
```

This creates:
- `dist/reachgenie-x.x.x.tar.gz` (source distribution)
- `dist/reachgenie-x.x.x-py3-none-any.whl` (wheel distribution)

### 4. Check the Build

```bash
twine check dist/*
```

### 5. Upload to TestPyPI (Optional but Recommended)

First, test on TestPyPI:

```bash
twine upload --repository testpypi dist/*
```

You'll be prompted for credentials:
- Username: `__token__`
- Password: your TestPyPI API token (including the `pypi-` prefix)

Then test install:
```bash
pip install --index-url https://test.pypi.org/simple/ reachgenie
```

### 6. Upload to PyPI (Production)

```bash
twine upload dist/*
```

You'll be prompted for credentials:
- Username: `__token__`
- Password: your PyPI API token (including the `pypi-` prefix)

### 7. Verify Installation

```bash
pip install reachgenie
```

## Automated Publishing with GitHub Actions

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build twine

      - name: Build package
        run: python -m build

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

### Setting up GitHub Secret

1. Go to your repository on GitHub
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `PYPI_API_TOKEN`
5. Value: Your PyPI API token

Now when you create a GitHub release, it will automatically publish to PyPI!

## Creating a Release

1. Update version numbers
2. Commit changes
3. Create a git tag:
```bash
git tag -a v0.1.0 -m "Release version 0.1.0"
git push origin v0.1.0
```

4. Create a release on GitHub:
   - Go to https://github.com/alinaqi/reachgenie/releases/new
   - Select your tag
   - Add release notes
   - Publish release

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

Examples:
- `0.1.0` - Initial beta release
- `0.1.1` - Bug fix
- `0.2.0` - New feature
- `1.0.0` - First stable release

## Troubleshooting

### Package Name Already Taken
If `reachgenie` is taken, you can use:
- `reachgenie-ai`
- `reachgenie-sdr`
- Update the `name` field in `setup.py` and `pyproject.toml`

### Build Errors
- Ensure all required files are in `MANIFEST.in`
- Check that `requirements.txt` is up to date
- Verify Python version compatibility

### Upload Errors
- Check your API token is correct
- Ensure you're using `__token__` as username
- Verify network connectivity

## Resources

- PyPI: https://pypi.org/
- Packaging Guide: https://packaging.python.org/
- Twine Documentation: https://twine.readthedocs.io/
