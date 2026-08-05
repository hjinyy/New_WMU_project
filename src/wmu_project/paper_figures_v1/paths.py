from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PFPaths:
    repo_root: Path
    data_root: Path
    output_root: Path

    @property
    def basic_results(self) -> Path:
        return self.data_root / "analysis_basic_v1" / "results_basic_v1"

    @property
    def basic_features(self) -> Path:
        return self.data_root / "analysis_basic_v1" / "features_basic_v1"

    @property
    def fg_root(self) -> Path:
        return self.data_root / "analysis_basic_v1" / "analysis_fault_generalization_v1"

    @property
    def fg_results(self) -> Path:
        return self.fg_root / "results"

    @property
    def fg_features(self) -> Path:
        return self.fg_root / "features"

    @property
    def basic_manifest_14(self) -> Path:
        return self.data_root / "IEEE14bus" / "manifests" / "case_manifest.csv"

    @property
    def basic_manifest_30(self) -> Path:
        return self.data_root / "IEEE30bus" / "manifests" / "case_manifest_30bus.csv"

    @property
    def basic_raw_14(self) -> Path:
        return self.data_root / "raw_csv"

    @property
    def basic_raw_30(self) -> Path:
        return self.data_root / "IEEE30bus" / "raw_csv"

    @property
    def figures_png(self) -> Path:
        return self.output_root / "figures_png"

    @property
    def figures_pdf(self) -> Path:
        return self.output_root / "figures_pdf"

    @property
    def figure_data(self) -> Path:
        return self.output_root / "figure_data"

    @property
    def captions(self) -> Path:
        return self.output_root / "captions"

    @property
    def diagnostics(self) -> Path:
        return self.output_root / "diagnostics"

    def ensure(self) -> None:
        for p in [
            self.figures_png,
            self.figures_pdf,
            self.figure_data,
            self.captions,
            self.diagnostics,
            self.output_root / "scripts",
        ]:
            p.mkdir(parents=True, exist_ok=True)


IEEE14_BRANCHES = [(1,2),(1,5),(2,3),(2,4),(2,5),(3,4),(4,5),(4,7),(4,9),(5,6),
                   (6,11),(6,12),(6,13),(7,8),(7,9),(9,10),(9,14),(10,11),(12,13),(13,14)]
IEEE30_BRANCHES = [(1,2),(1,3),(2,4),(3,4),(2,5),(2,6),(4,6),(5,7),(6,7),(6,8),
                   (6,9),(6,10),(9,11),(9,10),(4,12),(12,13),(12,14),(12,15),(12,16),(14,15),
                   (16,17),(15,18),(18,19),(19,20),(10,20),(10,17),(10,21),(10,22),(21,22),(15,23),
                   (22,24),(23,24),(24,25),(25,26),(25,27),(28,27),(27,29),(27,30),(29,30),(8,28),(6,28)]
PCC_BUS = {"ieee14": 7, "ieee30": 30}
REP_BUSES = {"ieee14": [2, 6, 9, 11, 14], "ieee30": [1, 6, 10, 24, 30]}
NBUSES = {"ieee14": 14, "ieee30": 30}
EVENT_ORDER = ["Normal", "LoadSwitch", "CapSwitch", "SLG", "LL", "LLG", "ThreePhase"]
FAULT_TYPES = ["SLG", "LL", "LLG", "ThreePhase"]
