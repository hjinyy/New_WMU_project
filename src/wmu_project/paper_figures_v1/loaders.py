"""Loaders + topology utilities."""
from __future__ import annotations
from pathlib import Path
import networkx as nx
import numpy as np
import pandas as pd

from .paths import IEEE14_BRANCHES, IEEE30_BRANCHES, NBUSES


def branches(network_id: str) -> list[tuple[int, int]]:
    return IEEE14_BRANCHES if network_id == "ieee14" else IEEE30_BRANCHES


def graph_for(network_id: str) -> nx.Graph:
    g = nx.Graph()
    g.add_nodes_from(range(1, NBUSES[network_id] + 1))
    g.add_edges_from(branches(network_id))
    return g


def hop_distance(g: nx.Graph, src: int) -> dict[int, int]:
    return dict(nx.single_source_shortest_path_length(g, src))


def load_waveform_csv(path: Path, n_buses: int) -> pd.DataFrame:
    # Sniff header
    with open(path, "r") as f:
        first = f.readline()
    has_header = "Time" in first
    if has_header:
        df = pd.read_csv(path)
    else:
        cols = ["Time"]
        for b in range(1, n_buses + 1):
            for ph in ("a", "b", "c"):
                cols.append(f"V{ph}_{b}")
            for ph in ("a", "b", "c"):
                cols.append(f"I{ph}_{b}")
        df = pd.read_csv(path, header=None, names=cols)
    df.columns = [c.strip() for c in df.columns]
    return df


def basic_manifest(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Normalise raw path column so we can resolve local copies
    if "OutputCSV" in df.columns:
        df["Basename"] = df["OutputCSV"].astype(str).str.rsplit("/", n=1).str[-1]
    return df


def resolve_raw(basename: str, raw_dir: Path) -> Path | None:
    p = raw_dir / basename
    return p if p.exists() else None
