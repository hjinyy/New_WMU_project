from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class SyntheticRadialNetwork:
    """Declared synthetic linearized network used only for optimizer tests.

    Edge impedances and measurement matrix are deliberately synthetic; no result
    produced with this object may be labelled as an IEEE14/IEEE30 result.
    """

    n_bus: int
    edges: tuple[tuple[int, int, float], ...]
    measurement_buses: tuple[int, ...]

    def laplacian(self) -> np.ndarray:
        l = np.zeros((self.n_bus, self.n_bus), dtype=float)
        for a, b, r in self.edges:
            g = 1.0 / float(r)
            a -= 1; b -= 1
            l[a, a] += g; l[b, b] += g; l[a, b] -= g; l[b, a] -= g
        # Reference bus 1 is grounded in the reduced nodal equation.
        return l[1:, 1:]

    def response_library(self) -> dict[int, np.ndarray]:
        y = self.laplacian()
        inv = np.linalg.inv(y)
        out: dict[int, np.ndarray] = {}
        for bus in range(1, self.n_bus + 1):
            if bus == 1:
                v = np.zeros(self.n_bus)
            else:
                inj = np.zeros(self.n_bus - 1); inj[bus - 2] = 1.0
                v = np.concatenate([[0.0], inv @ inj])
            # Voltage responses at measurement buses plus edge-current proxy.
            volt = v[np.asarray(self.measurement_buses) - 1]
            cur = []
            for a, b, r in self.edges:
                cur.append((v[a - 1] - v[b - 1]) / r)
            out[bus] = np.concatenate([volt, np.asarray(cur)])
        return out


def make_synthetic_radial_network() -> SyntheticRadialNetwork:
    # Explicit synthetic Ohm-equivalent weights for a five-bus radial feeder.
    return SyntheticRadialNetwork(
        n_bus=5,
        edges=((1, 2, 0.12), (2, 3, 0.18), (2, 4, 0.25), (4, 5, 0.16)),
        measurement_buses=(2, 3, 4, 5),
    )


def simulate_fault_response(
    network: SyntheticRadialNetwork,
    bus: int,
    amplitude: float,
    gaussian_sigma: float,
    gross_error: float = 0.0,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    rng = np.random.default_rng() if rng is None else rng
    h = network.response_library()[int(bus)]
    y = float(amplitude) * h + rng.normal(0.0, float(gaussian_sigma), size=h.size)
    if gross_error:
        # Deterministic-format non-Gaussian perturbation: a random signed spike.
        j = int(rng.integers(0, h.size))
        y[j] += float(gross_error) * (1.0 if rng.random() >= 0.5 else -1.0)
    return y
