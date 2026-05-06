"""Raw-data import and staged live-state generation from data_import.ipynb."""

from __future__ import annotations

import heapq
from pathlib import Path

import numpy as np
import pandas as pd

from bsc_fgi_scheduler.constants import CENTERLINES, FGI_CPJ, FGI_STAFFING_BYSHIFT
from bsc_fgi_scheduler.dataframes import (
    build_ap_data,
    build_labor_data,
    build_location_data,
    clean_fa_status,
    clean_node_data,
)
from bsc_fgi_scheduler.export import export_live_state
from bsc_fgi_scheduler.paths import DATA_RAW_DIR, DATA_STAGED_DIR, OUTPUT_DIR, get_default_filepaths


def load_fa_status(filepath: str | Path | None = None, simulated: bool = False) -> pd.DataFrame:
    filepath = get_default_filepaths()["FAstatus"] if filepath is None else Path(filepath)
    sheet_name = "FARO_simulated_rates" if simulated else "FARO_Scorecard"
    header = 0 if simulated else 2
    return pd.read_excel(filepath, sheet_name=sheet_name, header=header, engine="openpyxl")


def load_p3_milestones(filepath: str | Path | None = None, simulated: bool = False) -> pd.DataFrame:
    filepath = get_default_filepaths()["FAstatus"] if filepath is None else Path(filepath)
    sheet_name = "P3_Milestones_detail" if simulated else "P3 Milestone Detail"
    return pd.read_excel(filepath, sheet_name=sheet_name, engine="openpyxl")


def load_tank_closure(filepath: str | Path | None = None, simulated: bool = False) -> pd.DataFrame:
    filepath = get_default_filepaths()["FAstatus"] if filepath is None else Path(filepath)
    sheet_name = "Tank_Closure_detail" if simulated else "Tank_Closure_Detail"
    return pd.read_excel(filepath, sheet_name=sheet_name, engine="openpyxl")


def load_fa_priority(filepath: str | Path | None = None) -> pd.DataFrame:
    filepath = get_default_filepaths()["FGI_Locations"] if filepath is None else Path(filepath)
    fa_priority = pd.read_excel(filepath, sheet_name="FA Priority", header=1, engine="openpyxl")
    return (
        fa_priority.drop(columns=[c for c in fa_priority.columns if str(c).startswith("Unnamed")], errors="ignore")
        .dropna(how="all")
        .reset_index(drop=True)
    )


def load_nodes(filepath: str | Path | None = None):
    filepath = get_default_filepaths()["Nodes"] if filepath is None else Path(filepath)
    nodes = pd.read_excel(filepath, sheet_name="Node", engine="openpyxl")
    node_adj = pd.read_excel(filepath, sheet_name="adjacency", engine="openpyxl")
    return clean_node_data(nodes, node_adj)


def nodes_dataframe_to_dict(nodes_df: pd.DataFrame) -> dict:
    nodes_df = nodes_df.copy()
    nodes_df.columns = nodes_df.columns.str.strip()
    valid_node_rows = nodes_df[
        nodes_df["node_id"].notna()
        & nodes_df["x"].notna()
        & nodes_df["y"].notna()
    ].copy()
    nodes = {}
    for _, row in valid_node_rows.iterrows():
        node_id = str(row["node_id"]).strip()
        nodes[node_id] = {
            "id": node_id,
            "coord": [float(row["x"]), float(row["y"])],
            "type": row["type"] if "type" in nodes_df.columns else None,
            "req_centerline": row["req_centerline"] if "req_centerline" in nodes_df.columns else None,
        }
    return nodes


def build_neighbor_map(nodes: dict, adjacency_df: pd.DataFrame) -> dict:
    adjacency_df = adjacency_df.copy()
    adjacency_df.columns = adjacency_df.columns.str.strip()
    neighbor_map = {node_id: [] for node_id in nodes}
    blocked_edges = {
        ("FGI1", "P3SW"),
        ("FGI2", "FGI1"),
        ("FGI3", "FGI2"),
        ("FGI4", "FGI3"),
        ("N38", "FGI4"),
    }
    valid_edge_rows = adjacency_df[
        adjacency_df["from_node"].notna()
        & adjacency_df["to_node"].notna()
    ].copy()
    for _, row in valid_edge_rows.iterrows():
        u = str(row["from_node"]).strip()
        v = str(row["to_node"]).strip()
        if u in nodes and v in nodes and u != v:
            if (u, v) not in blocked_edges:
                neighbor_map[u].append(v)
            if (v, u) not in blocked_edges:
                neighbor_map[v].append(u)
    for node_id in neighbor_map:
        neighbor_map[node_id] = list(dict.fromkeys(neighbor_map[node_id]))
    return neighbor_map


def point_distance(nodes, a, b):
    x1, y1 = nodes[a]["coord"]
    x2, y2 = nodes[b]["coord"]
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def greedy_route(nodes, neighbor_map, origin, destination):
    if origin not in nodes or destination not in nodes:
        return None
    if origin == destination:
        return {"total_distance": 0.0}
    best_distance = {origin: 0.0}
    frontier = [(0.0, origin)]
    while frontier:
        current_distance, current = heapq.heappop(frontier)
        if current == destination:
            break
        for next_node in neighbor_map.get(current, []):
            segment_distance = point_distance(nodes, current, next_node)
            new_distance = current_distance + segment_distance
            if new_distance < best_distance.get(next_node, np.inf):
                best_distance[next_node] = new_distance
                heapq.heappush(frontier, (new_distance, next_node))
    if destination not in best_distance:
        return None
    return {"total_distance": best_distance[destination]}


def calc_move_time(route_info, speed_mph=3):
    if route_info is None:
        return np.inf
    distance_feet = route_info["total_distance"]
    distance_miles = distance_feet / 5280
    return distance_miles / speed_mph


def build_move_time_matrices(nodes: dict, neighbor_map: dict, speed_mph=3):
    node_ids = list(nodes.keys())
    distance_matrix = pd.DataFrame(np.inf, index=node_ids, columns=node_ids)
    move_time_matrix = pd.DataFrame(np.inf, index=node_ids, columns=node_ids)
    for origin in node_ids:
        for destination in node_ids:
            route_info = greedy_route(nodes, neighbor_map, origin, destination)
            if origin == destination:
                distance_matrix.loc[origin, destination] = 0.0
                move_time_matrix.loc[origin, destination] = 0.0
            elif route_info is not None:
                distance_matrix.loc[origin, destination] = route_info["total_distance"]
                move_time_matrix.loc[origin, destination] = calc_move_time(route_info, speed_mph=speed_mph)
    return distance_matrix, move_time_matrix


def export_move_time_matrices(move_time_matrix: pd.DataFrame, distance_matrix: pd.DataFrame, output_file: str | Path):
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    report_move_times = move_time_matrix.copy()
    report_distance = distance_matrix.copy()
    report_move_times.index.name = "from_loc"
    report_distance.index.name = "from_loc"
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        report_move_times.reset_index().to_excel(writer, sheet_name="location_move_times", index=False)
        report_distance.reset_index().to_excel(writer, sheet_name="distance_matrix", index=False)
    return output_file


def load_historical_move_times(hist_file: str | Path | None = None):
    hist_file = DATA_RAW_DIR / "Centerlines and Move Times Purdue.xlsx" if hist_file is None else Path(hist_file)
    hist_xl = pd.read_excel(hist_file, sheet_name="Move Times", engine="openpyxl")
    hist_xl.columns = hist_xl.columns.str.strip()
    hist = hist_xl[["Starting Position", "Move Time", "Ending Position", "Centerline"]].copy()
    hist = hist.rename(columns={
        "Starting Position": "start",
        "Move Time": "historical_move_time",
        "Ending Position": "end",
    })
    hist = hist[hist["Centerline"].fillna("").astype(str).str.upper() != "Y"].copy()
    hist = hist[["start", "historical_move_time", "end"]]
    hist["start"] = hist["start"].astype(str).str.strip()
    hist["end"] = hist["end"].astype(str).str.strip()
    hist["historical_move_time"] = pd.to_numeric(hist["historical_move_time"], errors="coerce")
    hist = hist.dropna(subset=["historical_move_time"])
    q1 = hist["historical_move_time"].quantile(0.25)
    q3 = hist["historical_move_time"].quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    return hist[
        (hist["historical_move_time"] >= lower_bound)
        & (hist["historical_move_time"] <= upper_bound)
    ].copy()


def compare_modeled_move_times(move_time_matrix: pd.DataFrame, hist_clean: pd.DataFrame):
    model_long = (
        move_time_matrix.reset_index()
        .rename(columns={"index": "start"})
        .melt(id_vars="start", var_name="end", value_name="modeled_move_time")
    )
    model_long = model_long[model_long["start"] != model_long["end"]].copy()
    comparison = hist_clean.merge(model_long, on=["start", "end"], how="inner")
    comparison = comparison[np.isfinite(comparison["modeled_move_time"])].copy()
    comparison["error"] = comparison["modeled_move_time"] - comparison["historical_move_time"]
    comparison["abs_error"] = comparison["error"].abs()
    comparison["pct_error"] = comparison["error"] / comparison["historical_move_time"]
    return comparison


def calibrate_move_time_matrix(move_time_matrix: pd.DataFrame, comparison: pd.DataFrame):
    from sklearn.linear_model import LinearRegression

    x = comparison[["modeled_move_time"]]
    y = comparison["historical_move_time"]
    linear_model = LinearRegression()
    linear_model.fit(x, y)
    intercept = linear_model.intercept_
    slope = linear_model.coef_[0]
    linear_calibrated_move_time_matrix = (move_time_matrix * slope) + intercept
    for loc in linear_calibrated_move_time_matrix.index:
        linear_calibrated_move_time_matrix.loc[loc, loc] = 0
    return linear_calibrated_move_time_matrix, intercept, slope


def export_calibrated_move_time_matrix(linear_calibrated_move_time_matrix: pd.DataFrame, output_file: str | Path):
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    report_linear_calibrated = linear_calibrated_move_time_matrix.copy()
    report_linear_calibrated.index.name = "from_loc"
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        report_linear_calibrated.reset_index().to_excel(writer, sheet_name="location_move_times", index=False)
    return output_file


def generate_node_map(nodes: dict, neighbor_map: dict, output_file: str | Path | None = None):
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    output_file = OUTPUT_DIR / "nodemap.png" if output_file is None else Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    node_coords = pd.DataFrame(
        [{"node_id": node_id, "x": attrs["coord"][0], "y": attrs["coord"][1]} for node_id, attrs in nodes.items()]
    ).sort_values(["y", "x", "node_id"])
    fig, ax = plt.subplots(figsize=(34, 20), dpi=220)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fbfbf7")
    drawn_edges = set()
    for from_node, to_nodes in neighbor_map.items():
        for to_node in to_nodes:
            if from_node not in nodes or to_node not in nodes:
                continue
            edge_key = tuple(sorted((from_node, to_node)))
            if edge_key in drawn_edges:
                continue
            x1, y1 = nodes[from_node]["coord"]
            x2, y2 = nodes[to_node]["coord"]
            ax.plot([x1, x2], [y1, y2], color="#a9a9a9", linewidth=2.2, alpha=0.55, zorder=1)
            drawn_edges.add(edge_key)
    ax.scatter(node_coords["x"], node_coords["y"], s=360, color="#1769aa", edgecolor="white", linewidth=2.0, zorder=3)
    label_offsets = [(18, 18), (18, -22), (-18, 18), (-18, -22), (0, 28), (0, -32)]
    for idx, row in node_coords.reset_index(drop=True).iterrows():
        dx, dy = label_offsets[idx % len(label_offsets)]
        ax.annotate(
            row["node_id"],
            xy=(row["x"], row["y"]),
            xytext=(dx, dy),
            textcoords="offset points",
            ha="center",
            va="center",
            fontsize=18,
            fontweight="bold",
            color="#111111",
            bbox={"boxstyle": "round,pad=0.22", "facecolor": "white", "edgecolor": "#666666", "alpha": 0.92},
            arrowprops={"arrowstyle": "-", "color": "#555555", "linewidth": 1.0, "alpha": 0.65},
            zorder=4,
        )
    ax.set_title("BSC FGI Scheduler Node Map", fontsize=30, fontweight="bold", pad=24)
    ax.set_xlabel("X coordinate", fontsize=20, labelpad=12)
    ax.set_ylabel("Y coordinate", fontsize=20, labelpad=12)
    ax.tick_params(axis="both", labelsize=16)
    ax.grid(True, color="#d9d9d9", linewidth=1.0, alpha=0.8)
    ax.set_aspect("equal", adjustable="box")
    x_padding = max((node_coords["x"].max() - node_coords["x"].min()) * 0.08, 300)
    y_padding = max((node_coords["y"].max() - node_coords["y"].min()) * 0.16, 300)
    ax.set_xlim(node_coords["x"].min() - x_padding, node_coords["x"].max() + x_padding)
    ax.set_ylim(node_coords["y"].min() - y_padding, node_coords["y"].max() + y_padding)
    legend_items = [
        Line2D([0], [0], color="#a9a9a9", linewidth=2.2, label="Allowed connection"),
        Line2D([0], [0], marker="o", color="w", label="Node", markerfacecolor="#1769aa", markeredgecolor="white", markersize=14),
    ]
    ax.legend(handles=legend_items, loc="upper left", fontsize=16, frameon=True, facecolor="white", edgecolor="#777777")
    plt.tight_layout()
    fig.savefig(output_file, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output_file


def import_data(rootpath: str | Path | None = None, filepaths: dict | None = None, simulated: bool = False):
    if filepaths is None:
        filepaths = get_default_filepaths(Path(rootpath)) if rootpath is not None else get_default_filepaths()
    faro_scorecard = load_fa_status(filepaths["FAstatus"], simulated=simulated)
    tank_closure = load_tank_closure(filepaths["FAstatus"], simulated=simulated)
    p3_milestones = load_p3_milestones(filepaths["FAstatus"], simulated=simulated)
    fa_priority = load_fa_priority(filepaths["FGI_Locations"])
    nodes, node_adj = load_nodes(filepaths["Nodes"])
    faro_scorecard, tank_closure, p3_milestones = clean_fa_status(faro_scorecard, tank_closure, p3_milestones)
    return faro_scorecard, tank_closure, p3_milestones, fa_priority, nodes, node_adj


def build_live_state_workbook(
    fa_status_path: str | Path | None = None,
    locations_path: str | Path | None = None,
    move_times_path: str | Path | None = None,
    paint_schedule_path: str | Path | None = None,
    output_path: str | Path | None = None,
    simulated: bool | None = None,
    centerlines: dict | None = None,
):
    paths = get_default_filepaths()
    fa_status_path = paths["FAstatus"] if fa_status_path is None else Path(fa_status_path)
    locations_path = paths["FGI_Locations"] if locations_path is None else Path(locations_path)
    move_times_path = paths["Move Times"] if move_times_path is None else Path(move_times_path)
    paint_schedule_path = paths["Paint Schedule"] if paint_schedule_path is None else Path(paint_schedule_path)
    output_path = DATA_STAGED_DIR / "FGI_liveState.xlsx" if output_path is None else Path(output_path)

    if simulated is None:
        xl = pd.ExcelFile(fa_status_path, engine="openpyxl")
        simulated = "FARO_simulated_rates" in xl.sheet_names

    faro_scorecard = load_fa_status(fa_status_path, simulated=simulated)
    tank_closure = load_tank_closure(fa_status_path, simulated=simulated)
    p3_milestones = load_p3_milestones(fa_status_path, simulated=simulated)
    faro_scorecard, tank_closure, p3_milestones = clean_fa_status(faro_scorecard, tank_closure, p3_milestones)

    fa_priority = load_fa_priority(locations_path)
    ap_df = build_ap_data(faro_scorecard, p3_milestones, tank_closure)
    location_df = build_location_data(fa_priority=fa_priority, centerlines=CENTERLINES if centerlines is None else centerlines)
    labor_df = build_labor_data(fgi_staffing_byshift=FGI_STAFFING_BYSHIFT, fgi_cpj=FGI_CPJ)

    move_times_df = pd.read_excel(move_times_path, sheet_name="location_move_times", index_col=0)
    move_times_df.index = move_times_df.index.astype(str)
    move_times_df.columns = move_times_df.columns.astype(str)

    paint_schedule_df = pd.read_excel(
        paint_schedule_path,
        sheet_name="Historical",
        header=2,
        engine="openpyxl",
    )[["Date", "BSC1", "BSC2"]].copy()
    paint_schedule_df["Date"] = pd.to_datetime(paint_schedule_df["Date"], errors="coerce").dt.normalize()
    paint_schedule_df = paint_schedule_df[paint_schedule_df["Date"].notna()].reset_index(drop=True)

    export_live_state(ap_df, location_df, labor_df, move_times_df, paint_schedule_df, output_path)
    return ap_df, location_df, labor_df


# Compatibility aliases from notebook naming.
clean_FAstatus = clean_fa_status
clean_nodeData = clean_node_data
build_ap_df = build_ap_data
build_location_df = build_location_data
build_labor_df = build_labor_data
buildAPdata = build_ap_data
buildLocationdata = build_location_data
buildLabordata = build_labor_data
