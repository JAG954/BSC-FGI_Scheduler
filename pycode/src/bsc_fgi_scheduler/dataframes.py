"""Dataframe builders and staged-workbook loaders from the notebooks."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from bsc_fgi_scheduler.ap import AP
from bsc_fgi_scheduler.config import filepaths, rootpath
from bsc_fgi_scheduler.constants import CENTERLINES, FGI_CPJ as DEFAULT_FGI_CPJ, FGI_STAFFING_BYSHIFT as DEFAULT_FGI_STAFFING_BYSHIFT
from bsc_fgi_scheduler.location import Location
from bsc_fgi_scheduler.paths import PROJECT_ROOT

FGI_STAFFING_BYSHIFT = DEFAULT_FGI_STAFFING_BYSHIFT.copy()
FGI_CPJ = DEFAULT_FGI_CPJ.copy()


def merge_ap_data(faro_scorecard: pd.DataFrame, p3_milestones: pd.DataFrame, tank_closure: pd.DataFrame) -> pd.DataFrame:
    tank_lookup = (
        tank_closure[["LINE_NUMBER", "TankStatus"]]
        .drop_duplicates(subset="LINE_NUMBER")
        .rename(columns={"LINE_NUMBER": "LN"})
    )
    p3_lookup = p3_milestones.rename(columns={"P": "LN"}).copy()

    faro_scorecard = faro_scorecard.copy()
    faro_scorecard["LN"] = pd.to_numeric(faro_scorecard["LN"], errors="coerce")
    tank_lookup["LN"] = pd.to_numeric(tank_lookup["LN"], errors="coerce")
    p3_lookup["LN"] = pd.to_numeric(p3_lookup["LN"], errors="coerce")

    faro_scorecard["LN"] = faro_scorecard["LN"].astype("Int64").astype(str)
    tank_lookup["LN"] = tank_lookup["LN"].astype("Int64").astype(str)
    p3_lookup["LN"] = p3_lookup["LN"].astype("Int64").astype(str)

    return faro_scorecard.merge(tank_lookup, on="LN", how="left").merge(p3_lookup, on="LN", how="left")


def build_ap_data(faro_scorecard: pd.DataFrame, p3_milestones: pd.DataFrame, tank_closure: pd.DataFrame) -> pd.DataFrame:
    ap_data = merge_ap_data(faro_scorecard, p3_milestones, tank_closure)
    rows = []

    milestone_defaults = {
        "Engine Hang": 0,
        "Flight Controls": 0,
        "Gear Swing": 0,
        "Medium Pressure Test": 0,
        "Oil On": 0,
        "Power On": 0,
        "Engine_Type": None,
        "Milestone_Completion_Percentage": 0,
    }

    for _, row in ap_data.iterrows():
        ln = int(float(row["LN"]))
        rows.append({
            "LN": ln,
            "FA RO": row["FA RO"],
            "FA RO to B1R": row["FA RO to B1R"],
            "Total Counters": row["Total Counters"],
            "TankStatus": row["TankStatus"],
            "Ceilings": row["Ceilings"],
            "Initial Tests Run": row["Initial Tests Run"],
            "BTG_tot": row["Total BTG"],
            "BTG_p0": row["P0 BTG"],
            "BTG_p1": row["P1 BTG"],
            "BTG_p2": row["P2 BTG"],
            "BTG_p3": row["P3 BTG"],
            "BTG_engines": row["Engines BTG"],
            "BTG_doors": row["Doors BTG"],
            "BTG_test": row["Test BTG"],
            "P3_Engine Hang": row.get("Engine Hang", milestone_defaults["Engine Hang"]),
            "P3_Flight Controls": row.get("Flight Controls", milestone_defaults["Flight Controls"]),
            "P3_Gear Swing": row.get("Gear Swing", milestone_defaults["Gear Swing"]),
            "P3_Medium Pressure Test": row.get("Medium Pressure Test", milestone_defaults["Medium Pressure Test"]),
            "P3_Oil On": row.get("Oil On", milestone_defaults["Oil On"]),
            "P3_Power On": row.get("Power On", milestone_defaults["Power On"]),
            "P3_Engine_Type": row.get("Engine_Type", milestone_defaults["Engine_Type"]),
            "P3_Milestone_Completion_Percentage": row.get("Milestone_Completion_Percentage", milestone_defaults["Milestone_Completion_Percentage"]),
            "shakes_complete": row["shakes_completed"],
            "shakes_req": row["shakes_req"],
        })

    return pd.DataFrame(rows)


def build_location_data(fa_priority: pd.DataFrame, centerlines: dict | None = None) -> pd.DataFrame:
    centerlines = CENTERLINES if centerlines is None else centerlines
    rows = []

    for _, row in fa_priority.iterrows():
        loc = row["Location"]
        centerline_deps = centerlines.get(loc, None)
        rows.append({
            "Location": loc,
            "Future State Priority": row["Future State Priority"],
            "Date Online": row["Date Online"],
            "Owner": row["Owner"],
            "tooling_jacking": row["Jacking"] == "Y",
            "tooling_wings": row["Wings"] == "Y",
            "tooling_tankClosure": row["Tank Closure"] == "Y",
            "centerline_dependencies": None if centerline_deps is None else ", ".join(centerline_deps),
            "obstructions": None,
            "notes": None,
        })

    return pd.DataFrame(rows)


def build_labor_data(fgi_staffing_byshift: dict | None = None, fgi_cpj: dict | None = None) -> pd.DataFrame:
    fgi_staffing_byshift = DEFAULT_FGI_STAFFING_BYSHIFT if fgi_staffing_byshift is None else fgi_staffing_byshift
    fgi_cpj = DEFAULT_FGI_CPJ if fgi_cpj is None else fgi_cpj
    rows = []

    for shift, teams in fgi_staffing_byshift.items():
        for team, manhours in teams.items():
            rows.append({"category": "FGI_STAFFING_BYSHIFT", "shift": shift, "team": team, "value": manhours})

    for team, cpj in fgi_cpj.items():
        rows.append({"category": "FGI_CPJ", "shift": None, "team": team, "value": cpj})

    return pd.DataFrame(rows)


def clean_fa_status(faro_scorecard: pd.DataFrame, tank_closure: pd.DataFrame, p3_milestones: pd.DataFrame):
    faro_scorecard = faro_scorecard[pd.to_numeric(faro_scorecard["LN"], errors="coerce").notna()].copy()
    faro_scorecard = faro_scorecard.loc[:, ~faro_scorecard.columns.astype(str).str.contains(r"^Unnamed")]

    faro_scorecard[["shakes_completed", "shakes_req"]] = faro_scorecard["Zone Shakes"].astype(str).str.split("/", expand=True)
    faro_scorecard["p3_milestones"] = faro_scorecard["P3 Milestones"].astype(str).str.split("/").str[0]

    faro_scorecard = faro_scorecard.assign(
        LN=lambda df: pd.to_numeric(df["LN"], errors="coerce").astype(int),
        **{
            "FA RO to B1R": lambda df: pd.to_numeric(df["FA RO to B1R"], errors="coerce"),
            "Total Counters": lambda df: pd.to_numeric(df["Total Counters"], errors="coerce").fillna(0),
            "Total BTG": lambda df: pd.to_numeric(df["Total BTG"], errors="coerce").fillna(0),
            "P0 BTG": lambda df: pd.to_numeric(df["P0 BTG"], errors="coerce").fillna(0),
            "P1 BTG": lambda df: pd.to_numeric(df["P1 BTG"], errors="coerce").fillna(0),
            "P2 BTG": lambda df: pd.to_numeric(df["P2 BTG"], errors="coerce").fillna(0),
            "P3 BTG": lambda df: pd.to_numeric(df["P3 BTG"], errors="coerce").fillna(0),
            "Engines BTG": lambda df: pd.to_numeric(df["Engines BTG"], errors="coerce").fillna(0),
            "Doors BTG": lambda df: pd.to_numeric(df["Doors BTG"], errors="coerce").fillna(0),
            "Test BTG": lambda df: pd.to_numeric(df["Test BTG"], errors="coerce").fillna(0),
            "Tank Closure": lambda df: df["Tank Closure"].map({"Open": 0, "Closed": 1}).fillna(0).astype(int),
            "Ceilings": lambda df: pd.to_numeric(df["Ceilings"], errors="coerce").fillna(0),
            "Initial Tests Run": lambda df: (
                df["Initial Tests Run"].astype(str).str.replace("%", "", regex=False).replace("nan", 0).replace("", 0).astype(float) / 100
            ),
            "shakes_completed": lambda df: pd.to_numeric(df["shakes_completed"], errors="coerce").fillna(0).astype(int),
            "shakes_req": lambda df: pd.to_numeric(df["shakes_req"], errors="coerce").fillna(0).astype(int),
            "p3_milestones": lambda df: pd.to_numeric(df["p3_milestones"], errors="coerce").fillna(0).astype(int),
        },
    )

    tank_closure = tank_closure.copy()
    tank_closure["LINE_NUMBER"] = pd.to_numeric(tank_closure["LINE_NUMBER"], errors="coerce")
    tank_closure["Complete_Jobs"] = pd.to_numeric(tank_closure["Complete_Jobs"], errors="coerce").fillna(0)
    tank_closure["Total_Jobs"] = pd.to_numeric(tank_closure["Total_Jobs"], errors="coerce").fillna(0)
    tank_closure["TankStatus"] = tank_closure["TankStatus"].map({"Open": 0, "Closed": 1}).fillna(0).astype(int)

    p3_milestones = p3_milestones.copy().dropna(subset=["P"])
    p3_milestones["Engine_Type"] = p3_milestones["Milestone"].astype(str).str.extract(r"\((.*?)\)")
    p3_milestones["Milestone"] = p3_milestones["Milestone"].astype(str).str.replace(r"\s*\(.*?\)", "", regex=True)
    p3_milestones["P"] = pd.to_numeric(p3_milestones["P"], errors="coerce")
    p3_milestones["Completed_Jobs"] = pd.to_numeric(p3_milestones["Completed_Jobs"], errors="coerce").fillna(0)
    p3_milestones["STATUS (1 Complete, 0 Still Open)"] = pd.to_numeric(
        p3_milestones["STATUS (1 Complete, 0 Still Open)"], errors="coerce"
    ).fillna(0)

    milestone_completion = p3_milestones.groupby("P")["STATUS (1 Complete, 0 Still Open)"].mean()
    engine_type_lookup = p3_milestones.groupby("P")["Engine_Type"].first()
    p3_pivoted = (
        p3_milestones.pivot_table(index="P", columns="Milestone", values="Completed_Jobs", aggfunc="sum")
        .fillna(0)
        .reset_index()
    )
    p3_pivoted["Engine_Type"] = p3_pivoted["P"].map(engine_type_lookup)
    p3_pivoted["Milestone_Completion_Percentage"] = p3_pivoted["P"].map(milestone_completion)

    return faro_scorecard, tank_closure, p3_pivoted


def clean_node_data(nodes: pd.DataFrame, node_adj: pd.DataFrame):
    nodes = (
        nodes.drop(columns=[c for c in nodes.columns if str(c).startswith("Unnamed")], errors="ignore")
        .dropna(how="all")
        .assign(
            node_id=lambda df: df["node_id"].astype("string").str.strip(),
            x=lambda df: pd.to_numeric(df["x"], errors="coerce"),
            y=lambda df: pd.to_numeric(df["y"], errors="coerce"),
            type=lambda df: df["type"].astype("string").str.strip(),
            req_centerline=lambda df: df["req_centerline"].astype("string").str.strip(),
        )
        .replace({"": pd.NA})
        .dropna(subset=["node_id", "x", "y"])
        .reset_index(drop=True)
    )

    node_adj = (
        node_adj.drop(columns=[c for c in node_adj.columns if str(c).startswith("Unnamed")], errors="ignore")
        .dropna(how="all")
        .assign(
            from_node=lambda df: df["from_node"].astype("string").str.strip(),
            to_node=lambda df: df["to_node"].astype("string").str.strip(),
        )
        .replace({"": pd.NA})
        .dropna(subset=["from_node", "to_node"])
        .drop_duplicates()
        .reset_index(drop=True)
    )

    return nodes, node_adj


def parse_labor_config(labor_df: pd.DataFrame):
    staffing_rows = labor_df[labor_df["category"].eq("FGI_STAFFING_BYSHIFT")].copy()
    cpj_rows = labor_df[labor_df["category"].eq("FGI_CPJ")].copy()
    if staffing_rows.empty:
        raise ValueError("Missing FGI_STAFFING_BYSHIFT rows in sheet 'labor_data'")
    if cpj_rows.empty:
        raise ValueError("Missing FGI_CPJ rows in sheet 'labor_data'")
    staffing = {
        int(shift): group.set_index("team")["value"].astype(float).to_dict()
        for shift, group in staffing_rows.groupby("shift")
    }
    cpj = cpj_rows.set_index("team")["value"].astype(float).to_dict()
    return staffing, cpj


def load_live_state(path: str | Path | None = None, return_config: bool = False):
    global FGI_STAFFING_BYSHIFT, FGI_CPJ

    required_columns = {
        "ap_data": [
            "LN", "FA RO", "FA RO to B1R", "Total Counters", "TankStatus", "Ceilings",
            "Initial Tests Run", "BTG_tot", "BTG_p0", "BTG_p1", "BTG_p2", "BTG_p3",
            "BTG_engines", "BTG_doors", "BTG_test", "P3_Engine Hang",
            "P3_Flight Controls", "P3_Gear Swing", "P3_Medium Pressure Test",
            "P3_Oil On", "P3_Power On", "P3_Engine_Type",
            "P3_Milestone_Completion_Percentage", "shakes_complete", "shakes_req",
        ],
        "location_data": [
            "Location", "Future State Priority", "Date Online", "Owner",
            "tooling_jacking", "tooling_wings", "tooling_tankClosure",
            "centerline_dependencies", "obstructions", "notes",
        ],
        "labor_data": ["category", "shift", "team", "value"],
    }

    numeric_ap_columns = [
        "LN", "FA RO to B1R", "Total Counters", "TankStatus", "Ceilings",
        "Initial Tests Run", "BTG_tot", "BTG_p0", "BTG_p1", "BTG_p2", "BTG_p3",
        "BTG_engines", "BTG_doors", "BTG_test", "P3_Engine Hang",
        "P3_Flight Controls", "P3_Gear Swing", "P3_Medium Pressure Test",
        "P3_Oil On", "P3_Power On", "P3_Milestone_Completion_Percentage",
        "shakes_complete", "shakes_req",
    ]
    tooling_columns = ["tooling_jacking", "tooling_wings", "tooling_tankClosure"]

    def _normalize_bool(value):
        if pd.isna(value):
            return False
        if isinstance(value, (bool, np.bool_)):
            return bool(value)
        if isinstance(value, (int, float)):
            return value != 0
        value_str = str(value).strip().lower()
        if value_str in {"true", "t", "yes", "y", "1"}:
            return True
        if value_str in {"false", "f", "no", "n", "0", ""}:
            return False
        raise ValueError(f"Invalid boolean value in location_data: {value}")

    path = Path(path) if path is not None else PROJECT_ROOT / "data" / "staged" / "FGI_liveState.xlsx"
    path_candidates = [path]
    if not path.is_absolute():
        path_candidates.extend([PROJECT_ROOT / path, Path.cwd() / path, Path.cwd().parent / path])
    path = next((candidate for candidate in path_candidates if candidate.exists()), path)
    if not path.exists():
        raise ValueError(f"Live state workbook not found: {path}")

    workbook = pd.ExcelFile(path, engine="openpyxl")
    missing_sheets = [sheet for sheet in required_columns if sheet not in workbook.sheet_names]
    if missing_sheets:
        raise ValueError(f"Missing required sheet(s) in {path}: {', '.join(missing_sheets)}")

    ap_df = pd.read_excel(workbook, sheet_name="ap_data")
    location_df = pd.read_excel(workbook, sheet_name="location_data")
    labor_df = pd.read_excel(workbook, sheet_name="labor_data")
    frames = {"ap_data": ap_df, "location_data": location_df, "labor_data": labor_df}

    for sheet_name, expected_columns in required_columns.items():
        missing_columns = [col for col in expected_columns if col not in frames[sheet_name].columns]
        if missing_columns:
            raise ValueError(f"Missing required column(s) in sheet '{sheet_name}': {', '.join(missing_columns)}")

    ap_df = ap_df.copy()
    ap_df["FA RO"] = pd.to_datetime(ap_df["FA RO"], errors="coerce")
    for column in numeric_ap_columns:
        ap_df[column] = pd.to_numeric(ap_df[column], errors="coerce")
    if ap_df["LN"].notna().all():
        ap_df["LN"] = ap_df["LN"].astype("Int64")

    location_df = location_df.copy()
    location_df["Location"] = location_df["Location"].astype("string").str.strip()
    location_df = location_df[location_df["Location"].notna() & location_df["Location"].ne("")].reset_index(drop=True)
    for column in tooling_columns:
        location_df[column] = location_df[column].map(_normalize_bool).astype(bool)

    labor_df = labor_df.copy()
    labor_df["category"] = labor_df["category"].astype("string").str.strip()
    labor_df["team"] = labor_df["team"].astype("string").str.strip()
    labor_df["shift"] = pd.to_numeric(labor_df["shift"], errors="coerce").astype("Int64")
    labor_df["value"] = pd.to_numeric(labor_df["value"], errors="coerce")

    FGI_STAFFING_BYSHIFT, FGI_CPJ = parse_labor_config(labor_df)
    if return_config:
        return ap_df, location_df, labor_df, FGI_STAFFING_BYSHIFT, FGI_CPJ
    return ap_df, location_df, labor_df


def load_move_times(filepath: str | Path | None = None):
    filepath = filepaths["Move Times"] if filepath is None else Path(filepath)
    df = pd.read_excel(filepath, sheet_name="location_move_times", index_col=0)
    df.index = df.index.astype(str)
    df.columns = df.columns.astype(str)
    df = df.apply(pd.to_numeric, errors="coerce")
    return df.to_dict(orient="index")


def add_move_times(fgi, move_times):
    for from_loc, to_dict in move_times.items():
        if from_loc not in fgi.Locations:
            fgi.add_Location(from_loc, Location(priority=0, dateOnline="Now", name=from_loc))
        for to_loc in to_dict:
            if to_loc not in fgi.Locations:
                fgi.add_Location(to_loc, Location(priority=0, dateOnline="Now", name=to_loc))

    for from_loc, to_dict in move_times.items():
        loc_obj = fgi.Locations[from_loc]
        for to_loc, time in to_dict.items():
            loc_obj.set_time_to(to_loc, time)
    return fgi


def load_paint_schedule(filepath: str | Path | None = None, sheet_name="Historical"):
    filepath = filepaths["Paint Schedule"] if filepath is None else Path(filepath)
    paint_df = pd.read_excel(filepath, sheet_name=sheet_name, header=2, engine="openpyxl")
    paint_df = paint_df[["Date", "BSC1", "BSC2"]].copy()
    paint_df["Date"] = pd.to_datetime(paint_df["Date"], errors="coerce").dt.normalize()
    paint_df = paint_df[paint_df["Date"].notna()].reset_index(drop=True)

    paint_schedule = {}
    for _, row in paint_df.iterrows():
        date = row["Date"]
        paint_schedule[date] = {}
        for bay in ["BSC1", "BSC2"]:
            if pd.isna(row[bay]):
                paint_schedule[date][bay] = None
            else:
                paint_schedule[date][bay] = str(int(row[bay]))
    return paint_schedule


def init_aps(ap_df: pd.DataFrame):
    return {
        str(row["LN"]): AP(
            LN=int(row["LN"]),
            faro=row["FA RO"],
            toB1R=row["FA RO to B1R"],
            counters=row["Total Counters"],
            btg={
                "tot": row["BTG_tot"],
                "p0": row["BTG_p0"],
                "p1": row["BTG_p1"],
                "p2": row["BTG_p2"],
                "p3": row["BTG_p3"],
                "engines": row["BTG_engines"],
                "doors": row["BTG_doors"],
                "test": row["BTG_test"],
            },
            tankClosed=row["TankStatus"],
            ceilings=row["Ceilings"],
            testsRun=row["Initial Tests Run"],
            p3_milestones={
                "Engine Hang": row["P3_Engine Hang"],
                "Flight Controls": row["P3_Flight Controls"],
                "Gear Swing": row["P3_Gear Swing"],
                "Medium Pressure Test": row["P3_Medium Pressure Test"],
                "Oil On": row["P3_Oil On"],
                "Power On": row["P3_Power On"],
                "Engine_Type": row["P3_Engine_Type"],
                "Milestone_Completion_Percentage": row["P3_Milestone_Completion_Percentage"],
            },
            shakes={"complete": row["shakes_complete"], "req": row["shakes_req"]},
        )
        for _, row in ap_df.iterrows()
    }


def init_locations(location_df: pd.DataFrame):
    locations = {}
    for _, row in location_df.iterrows():
        if not pd.isna(row["Location"]):
            locations[row["Location"]] = Location(
                priority=row["Future State Priority"],
                dateOnline=row["Date Online"],
                name=row["Location"],
                owner=row["Owner"],
                tooling={
                    "jacking": row["tooling_jacking"],
                    "wings": row["tooling_wings"],
                    "tankClosure": row["tooling_tankClosure"],
                },
                centerlines=row["centerline_dependencies"],
            )
    return locations


# Notebook compatibility aliases.
merge_APdata = merge_ap_data
build_ap_df = build_ap_data
build_location_df = build_location_data
build_labor_df = build_labor_data
buildAPdata = build_ap_data
buildLocationdata = build_location_data
buildLabordata = build_labor_data
clean_FAstatus = clean_fa_status
clean_nodeData = clean_node_data
init_APs = init_aps
init_Locations = init_locations
