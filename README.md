# Pick Counter

Small Python project to count guitar picks in a selected image and export the result as JSON.

## Repository contents

- `src/`: application code
- `input/`: sample images
- `real_output/`: expected reference output for the example images
- `output/`: generated JSON files
- `THIRD_PARTY_LICENSES.md`: dependency license summary

## Requirements

- Python 3.12
- Dependencies from [requirements.txt](requirements.txt)

Install them in your environment with:

```powershell
python -m pip install -r requirements.txt
```

## Usage

Interactive mode with file picker:

```powershell
.\run.bat
```

Or directly:

```powershell
.\.venv\Scripts\python.exe src\pick_counter.py
```

Manual path mode is still available:

```powershell
.\.venv\Scripts\python.exe src\pick_counter.py input\example_1.jpg
```

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

Run lint locally with:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
```

The repository also includes a GitHub Actions workflow in `.github/workflows/ci.yml` that runs:

- `ruff`
- a smoke test on `example_1.jpg` to `example_6.jpg`
