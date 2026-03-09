# Pick Counter

Small Python project to count guitar picks in a selected image and export the result as JSON.

**Repository:** [https://github.com/DOKOS-TAYOS/PickCounter](https://github.com/DOKOS-TAYOS/PickCounter)

## Repository contents

- `src/`: application code
  - `config.py`: constants, paths, color definitions
  - `models.py`: data models (Candidate)
  - `io.py`: image I/O, validation, file dialogs
  - `detection.py`: pick detection (clear/textured backgrounds)
  - `classification.py`: color classification
  - `output.py`: JSON export and console output
  - `core.py`: main orchestration
  - `cli.py`: CLI entry point
- `output/`: generated JSON files
- `install.bat` / `install.sh`: full installation (clone, check deps, setup)
- `setup.bat` / `setup.sh`: environment setup (venv, dependencies)
- `run.bat` / `run.sh`: run the application
- `THIRD_PARTY_LICENSES.md`: dependency license summary

## Installation

### One-step install (recommended)

**Windows** — Download and run `install.bat`. It checks Git and Python (prompts download URLs if missing), clones the repo, and runs setup:

```batch
install.bat
```

**Linux / macOS** — Download and run `install.sh`. It installs Git and Python if needed, clones the repo, and runs setup:

```bash
sh install.sh
# or: chmod +x install.sh && ./install.sh
```

### Manual install

If you already have the repo cloned:

1. **Requirements:** Python 3.12, dependencies from [requirements.txt](requirements.txt)
2. **Setup:**
   - Windows: `setup.bat`
   - Linux/macOS: `./setup.sh`

## Usage

**Windows:**

```batch
run.bat
run.bat input\example_1.jpg
```

**Linux / macOS:**

```bash
./run.sh
./run.sh input/example_1.jpg
```

Without arguments, a file picker opens. With a path, that image is processed directly.

### Streamlit web app

To run the web app locally:

```bash
streamlit run streamlit_app.py
```

To deploy to [Streamlit Community Cloud](https://streamlit.io/cloud), connect your GitHub repo and set `streamlit_app.py` as the main file.

From Python:

```python
from src import counter_picks, counter_picks_from_dialog

result = counter_picks("input/example_1.jpg")
print(result)

dialog_result = counter_picks_from_dialog()
print(dialog_result)
```

The program prints the total number of picks and the count per approximate color, and writes:

```text
output/<image_name>.json
```

Example JSON:

```json
{
    "n_picks": 6,
    "colors": {
        "white": 3,
        "orange": 3
    }
}
```

## Detection backend

The project uses the built-in classical vision pipeline only.

## Supported color labels

The JSON output can currently use:

`black`, `gray`, `white`, `brown`, `red`, `orange`, `yellow`, `green`, `cyan`, `blue`, `purple`, `pink`

## Lint and CI

Run lint locally:

**Windows:**
```batch
.\.venv\Scripts\python.exe -m ruff check .
```

**Linux / macOS:**
```bash
./.venv/bin/python -m ruff check .
```

The repository includes a GitHub Actions workflow in `.github/workflows/ci.yml` that runs `ruff`.
