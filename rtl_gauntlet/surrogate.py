"""PPA surrogate (C3). A tiny pure-python ridge regressor so the data→model→eval loop
runs offline with no deps; the production surrogate is a GNN trained on GPU (see
docs/C3_PLAN.md). Predicts PPA from RTL features → fast proxy reward for the agent under
high-latency ground truth.
"""

from __future__ import annotations

from collections.abc import Sequence

FEATURE_KEYS = ["lines", "always", "assign", "case", "ff", "ops", "max_bits", "mux"]


def featurize(features: dict) -> list[float]:
    return [1.0] + [float(features.get(k, 0)) for k in FEATURE_KEYS]  # 1.0 = bias


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    """Gaussian elimination for the small normal-equation system."""
    n = len(a)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        m[col], m[piv] = m[piv], m[col]
        if abs(m[col][col]) < 1e-12:
            m[col][col] = 1e-12
        for r in range(n):
            if r != col:
                f = m[r][col] / m[col][col]
                for c in range(col, n + 1):
                    m[r][c] -= f * m[col][c]
    return [m[i][n] / m[i][i] for i in range(n)]


def ridge_fit(rows: Sequence[dict], target: str, lam: float = 1.0) -> list[float]:
    """Fit w minimizing ||Xw - y||^2 + lam||w||^2 over feature rows."""
    xs = [featurize(r["features"]) for r in rows]
    ys = [float(r[target]) for r in rows]
    d = len(xs[0])
    ata = [[sum(xs[k][i] * xs[k][j] for k in range(len(xs))) + (lam if i == j else 0.0)
            for j in range(d)] for i in range(d)]
    atb = [sum(xs[k][i] * ys[k] for k in range(len(xs))) for i in range(d)]
    return _solve(ata, atb)


def predict(w: list[float], features: dict) -> float:
    x = featurize(features)
    return sum(wi * xi for wi, xi in zip(w, x))


def pearson(a: Sequence[float], b: Sequence[float]) -> float:
    n = len(a)
    if n < 2:
        return float("nan")
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    va = sum((x - ma) ** 2 for x in a) ** 0.5
    vb = sum((x - mb) ** 2 for x in b) ** 0.5
    return cov / (va * vb) if va > 0 and vb > 0 else float("nan")
