"""Repository-relative path helpers for the BSC FGI Scheduler."""

from __future__ import annotations

from pathlib import Path


def get_project_root(start: Path | None = None) -> Path:
    """Find the repository root without hardcoding a user-specific path."""
    start = Path.cwd() if start is None else Path(start).resolve()
    candidates = [start, *start.parents]
    for path in candidates:
        if (path / "data").exists() and (path / "jupyter notebooks").exists():
            return path
        if (path / "pyproject.toml").exists() and (path / "src" / "bsc_fgi_scheduler").exists():
            return path
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = get_project_root()
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
DATA_STAGED_DIR = DATA_DIR / "staged"
DATA_SIMULATED_DIR = DATA_DIR / "simulated"
MOVE_TIMES_DIR = DATA_STAGED_DIR / "move_times"
OUTPUT_DIR = PROJECT_ROOT / "output"
NOTEBOOK_DIR = PROJECT_ROOT / "jupyter notebooks"


def get_default_filepaths(project_root: Path | None = None) -> dict[str, Path]:
    root = PROJECT_ROOT if project_root is None else Path(project_root)
    return {
        "FAstatus": root / "data" / "raw" / "FA_Status_FGI_Handoff.xlsx",
        "FGI_Locations": root / "data" / "raw" / "FGI_Locations_wPriority.xlsx",
        "Nodes": root / "data" / "raw" / "Nodes.xlsx",
        "Move Times": root / "data" / "staged" / "move_times" / "move_time_estimation.xlsx",
        "Paint Schedule": root / "data" / "raw" / "paint_schedules.xlsx",
        "Live State": root / "data" / "staged" / "FGI_liveState.xlsx",
    }


def ensure_output_dirs(output_dir: Path | None = None) -> Path:
    target = OUTPUT_DIR if output_dir is None else Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    return target
