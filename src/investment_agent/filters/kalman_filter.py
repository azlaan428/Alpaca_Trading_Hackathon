"""Kalman Filter — Price/Trend State Estimation Layer for X Quant X.

WHAT
====
Implements a 2D linear Kalman filter for single-asset price and trend estimation, filtering
noisy market price observations into posterior estimates of latent price, trend, and price variance.

WHY
===
Raw market price series contain microstructural noise and high-frequency volatility. Filtering
observed prices separates true price state and underlying trend from transient noise, producing
statistically sound state estimates and variance bounds required by downstream risk allocation layers.

HOW
===
- State Vector: x = [estimated_price, trend]ᵀ ∈ ℝ².
- Transition Matrix: F = [[1, dt], [0, 1]].
- Observation Matrix: H = [[1, 0]] (price only observed; trend latent).
- Predict-Correct Cycle: Joseph-form covariance update P(t|t) = (I - KH) P(t|t-1) (I - KH)ᵀ + K R Kᵀ
  with explicit symmetry enforcement and candidate pre-commit validation.

Mathematical Formulation
========================
Specified in high_level_proofs/finite_investment_architecture_as_economic_financial_fiscal_investment_kalman_filter.md.

State vector
------------
    x = [estimated_price, estimated_trend]^T   ∈ ℝ²

Transition model  (prediction step)
------------------------------------
    x(t|t-1) = F · x(t-1|t-1)

    F = [[1, dt],
         [0,  1]]

    Interpretation:
        price(t)  = price(t-1) + dt · trend(t-1)
        trend(t)  = trend(t-1)

Observation model
-----------------
    z(t) = H · x(t) + ν,     ν ~ N(0, R)

    H = [1, 0]

    We observe price only; trend is latent.

Process noise covariance
------------------------
    Q = [[q_price,  0      ],
         [0,        q_trend]]

    Irreducible market noise + aleatoric volatility.

Measurement noise variance
--------------------------
    R = r_price  (scalar measurement noise variance > 0)

Prediction step
---------------
    x̂(t|t-1) = F · x̂(t-1|t-1)
    P(t|t-1) = F · P(t-1|t-1) · F^T + Q

Correction step (measurement update — Joseph form for numerical stability)
-------------------------------------------------------------------------
    ỹ(t) = z(t) - H · x̂(t|t-1)              (innovation / residual)
    S(t) = H · P(t|t-1) · H^T + R           (innovation variance)
    K(t) = P(t|t-1) · H^T · S(t)⁻¹          (Kalman gain)
    x̂(t|t) = x̂(t|t-1) + K(t) · ỹ(t)          (updated state estimate)
    P(t|t) = (I - K·H) P(t|t-1) (I - K·H)^T + K·R·K^T  (Joseph form update)
    P(t|t) = (P(t|t) + P(t|t)^T) / 2          (enforced symmetry)

Transactional Update Guarantee
------------------------------
    All state transitions (prediction + correction) occur atomically.
    Candidate variables (`_x`, `_P`, `_innovation`, `_kalman_gain`, `_step`)
    are computed in local variables BEFORE committing to the instance state.
    If an update fails due to invalid inputs or numerical instability,
    the instance remains in its exact pre-update state without partial mutation.

Uncertainty representation
--------------------------
    price_uncertainty  = sqrt(P[0,0])  — standard deviation of price estimate
    trend_uncertainty  = sqrt(P[1,1])  — standard deviation of trend estimate
    Both are derived directly from the diagonal of the covariance matrix P.

Architectural Role
==================
Analytical estimation layer only. Feeds posterior KalmanState snapshots into the Seven-State
Capital Gate (capital_gate.py). Performs no order placement, execution, or state side-effects.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

import numpy as np


# ---------------------------------------------------------------------------
# Output container
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KalmanState:
    """Immutable snapshot of the Kalman filter's posterior state.

    All uncertainty values are derived from the posterior covariance matrix P.

    Attributes
    ----------
    estimated_price : float
        Posterior estimate of the latent price  (x̂[0]).
    trend : float
        Posterior estimate of the latent trend  (x̂[1]).
        Positive → price rising; negative → price falling.
    uncertainty : float
        Standard deviation of the price estimate  = sqrt(P[0,0]).
    trend_uncertainty : float
        Standard deviation of the trend estimate  = sqrt(P[1,1]).
    price_variance : float
        Posterior variance of the price estimate  = P[0,0].
    trend_variance : float
        Posterior variance of the trend estimate  = P[1,1].
    innovation : float
        Measurement innovation  ỹ = z - H · x̂(t|t-1).
        Represents the "news" component of the latest observation.
    kalman_gain_price : float
        Kalman gain for the price component  K[0].
        Fraction of innovation applied to the price estimate.
    """

    estimated_price: float
    trend: float
    uncertainty: float
    trend_uncertainty: float
    price_variance: float
    trend_variance: float
    innovation: float
    kalman_gain_price: float


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

def _validate_price(price: float, label: str = "price") -> float:
    """Validate that *price* is a numeric, finite, positive number.

    Parameters
    ----------
    price : float
        Observed or initial price value.
    label : str
        Human-readable label used in error messages.

    Returns
    -------
    float
        The validated price as a float.

    Raises
    ------
    TypeError
        If *price* is not a numeric type (or is a boolean).
    ValueError
        If *price* is NaN, infinite, zero, or negative.
    """
    if isinstance(price, bool) or not isinstance(price, (int, float, np.integer, np.floating)):
        raise TypeError(f"{label} must be numeric, got {type(price).__name__}")

    price = float(price)

    if math.isnan(price):
        raise ValueError(f"{label} must not be NaN")
    if math.isinf(price):
        raise ValueError(f"{label} must be finite, got {'inf' if price > 0 else '-inf'}")
    if price <= 0.0:
        raise ValueError(f"{label} must be positive, got {price}")

    return price


def _validate_positive_float(value: float, label: str) -> float:
    """Validate that a configuration parameter is numeric, finite, and strictly positive (> 0).

    Parameters
    ----------
    value : float
        Configuration parameter value.
    label : str
        Human-readable label used in error messages.

    Returns
    -------
    float
        The validated value as a float.

    Raises
    ------
    TypeError
        If *value* is not a numeric type (or is a boolean).
    ValueError
        If *value* is NaN, infinite, zero, or negative.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise TypeError(f"{label} must be numeric, got {type(value).__name__}")

    val = float(value)

    if math.isnan(val):
        raise ValueError(f"{label} must not be NaN")
    if math.isinf(val):
        raise ValueError(f"{label} must be finite, got {'inf' if val > 0 else '-inf'}")
    if val <= 0.0:
        raise ValueError(f"{label} must be strictly positive (> 0), got {val}")

    return val


# ---------------------------------------------------------------------------
# Kalman filter
# ---------------------------------------------------------------------------

class KalmanFilter:
    """Linear Kalman filter for financial price/trend state estimation.

    Parameters
    ----------
    initial_price : float
        First observed (or assumed) price. Must be positive and finite.
    dt : float, optional
        Time-step between observations (default 1.0). Must be strictly positive.
    process_noise_price : float, optional
        Diagonal element Q[0,0] — process noise variance for price (default 1e-4).
    process_noise_trend : float, optional
        Diagonal element Q[1,1] — process noise variance for trend (default 1e-6).
    measurement_noise : float, optional
        Scalar measurement noise variance R (default 1e-2).
    initial_price_variance : float, optional
        Initial P[0,0] — uncertainty in the price estimate (default 1.0).
    initial_trend_variance : float, optional
        Initial P[1,1] — uncertainty in the trend estimate (default 1.0).

    Raises
    ------
    TypeError
        If any argument is not numeric or is a boolean.
    ValueError
        If *initial_price* is non-positive/non-finite, or if any variance/noise/dt
        parameter is non-positive or non-finite.
    """

    # ---- construction -------------------------------------------------------

    def __init__(
        self,
        initial_price: float,
        *,
        dt: float = 1.0,
        process_noise_price: float = 1e-4,
        process_noise_trend: float = 1e-6,
        measurement_noise: float = 1e-2,
        initial_price_variance: float = 1.0,
        initial_trend_variance: float = 1.0,
    ) -> None:
        initial_price = _validate_price(initial_price, "initial_price")
        dt = _validate_positive_float(dt, "dt")
        process_noise_price = _validate_positive_float(process_noise_price, "process_noise_price")
        process_noise_trend = _validate_positive_float(process_noise_trend, "process_noise_trend")
        measurement_noise = _validate_positive_float(measurement_noise, "measurement_noise")
        initial_price_variance = _validate_positive_float(initial_price_variance, "initial_price_variance")
        initial_trend_variance = _validate_positive_float(initial_trend_variance, "initial_trend_variance")

        self._initial_price: float = initial_price
        self._initial_price_variance: float = initial_price_variance
        self._initial_trend_variance: float = initial_trend_variance
        self._dt: float = dt

        # State vector:  x = [price, trend]ᵀ
        self._x: np.ndarray = np.array([initial_price, 0.0], dtype=np.float64)

        # Posterior covariance:  P  (2×2, symmetric positive-definite)
        self._P: np.ndarray = np.array(
            [[initial_price_variance, 0.0],
             [0.0, initial_trend_variance]],
            dtype=np.float64,
        )

        # Transition matrix:  F = [[1, dt], [0, 1]]
        self._F: np.ndarray = np.array(
            [[1.0, dt],
             [0.0, 1.0]],
            dtype=np.float64,
        )

        # Observation matrix:  H = [1, 0]  (row vector)
        self._H: np.ndarray = np.array([[1.0, 0.0]], dtype=np.float64)

        # Process noise covariance:  Q  (diagonal)
        self._Q: np.ndarray = np.array(
            [[process_noise_price, 0.0],
             [0.0, process_noise_trend]],
            dtype=np.float64,
        )

        # Measurement noise variance:  R  (scalar, stored as 1×1)
        self._R: np.ndarray = np.array([[measurement_noise]], dtype=np.float64)

        # Identity matrix for covariance update
        self._I: np.ndarray = np.eye(2, dtype=np.float64)

        # Track the last innovation and gain for reporting
        self._innovation: float = 0.0
        self._kalman_gain: np.ndarray = np.zeros((2, 1), dtype=np.float64)

        # Step counter
        self._step: int = 0

    # ---- public interface ---------------------------------------------------

    def update(self, observed_price: float) -> KalmanState:
        """Incorporate a new price observation and return the updated state.

        Executes the full predict → correct cycle using local candidate variables,
        the Joseph-form covariance update, and strict pre-commit validation:

            1. **Validate input** — check observation validity.
            2. **Predict (local)** — propagate candidate state and covariance.
            3. **Correct (local)** — compute candidate innovation, Kalman gain,
               updated state, and Joseph-form covariance.
            4. **Validate candidate state** — check all candidate matrices for
               finiteness and non-negative diagonal variance BEFORE mutating internal state.
            5. **Commit (atomic)** — assign validated candidate variables to
               `self._x`, `self._P`, `self._innovation`, `self._kalman_gain`, and increment `self._step`.

        Parameters
        ----------
        observed_price : float
            The newly observed market price. Must be positive and finite.

        Returns
        -------
        KalmanState
            Frozen snapshot of the posterior state after the update.

        Raises
        ------
        TypeError
            If *observed_price* is not numeric or is a boolean.
        ValueError
            If *observed_price* is NaN, infinite, zero, or negative.
        RuntimeError
            If candidate calculations yield non-finite values or degenerate covariance.
        """
        # 1. Validate input parameter
        observed_price = _validate_price(observed_price, "observed_price")
        z = np.array([[observed_price]], dtype=np.float64)

        # 2. Local candidate prediction step
        x_pred = self._F @ self._x.reshape(2, 1)
        P_pred = self._F @ self._P @ self._F.T + self._Q

        # 3. Local candidate measurement update (correction step)
        y_innov = z - self._H @ x_pred
        S = self._H @ P_pred @ self._H.T + self._R

        s_val = float(S[0, 0])
        if math.isnan(s_val) or math.isinf(s_val) or s_val <= 0.0:
            raise RuntimeError(
                f"Kalman filter innovation covariance S is non-positive or non-finite ({s_val})."
            )

        S_inv = 1.0 / S  # 1×1 scalar inversion
        K = P_pred @ self._H.T @ S_inv
        x_upd = x_pred + K @ y_innov

        # 4. Local candidate Joseph-form covariance update & symmetry enforcement
        I_KH = self._I - K @ self._H
        P_upd = I_KH @ P_pred @ I_KH.T + K @ self._R @ K.T
        P_upd = 0.5 * (P_upd + P_upd.T)

        # 5. VALIDATE ALL CANDIDATE VALUES BEFORE MUTATING INTERNAL STATE
        if not np.all(np.isfinite(x_upd)):
            raise RuntimeError(
                "Kalman filter state vector estimate contains non-finite values."
            )
        if not np.all(np.isfinite(P_upd)):
            raise RuntimeError(
                "Kalman filter covariance matrix contains non-finite values. "
                "The filter has become numerically unstable."
            )
        if not np.all(np.isfinite(y_innov)):
            raise RuntimeError(
                "Kalman filter innovation contains non-finite values."
            )
        if not np.all(np.isfinite(K)):
            raise RuntimeError(
                "Kalman filter gain matrix contains non-finite values."
            )

        # Check covariance diagonal non-negativity
        if P_upd[0, 0] < -1e-12 or P_upd[1, 1] < -1e-12:
            raise RuntimeError(
                f"Kalman filter covariance diagonal became negative: P[0,0]={P_upd[0,0]}, P[1,1]={P_upd[1,1]}"
            )

        # Clip tiny negative numerical noise to zero
        if P_upd[0, 0] < 0.0:
            P_upd[0, 0] = 0.0
        if P_upd[1, 1] < 0.0:
            P_upd[1, 1] = 0.0

        # 6. ATOMIC COMMIT — only executed when all candidate validations succeed
        self._x = x_upd.flatten()
        self._P = P_upd
        self._innovation = float(y_innov[0, 0])
        self._kalman_gain = K
        self._step += 1

        return self._build_state()

    def get_state(self) -> KalmanState:
        """Return the current posterior state without performing an update.

        Calling `get_state()` is idempotent and has no side effects.

        Returns
        -------
        KalmanState
            Frozen snapshot of the current state.
        """
        return self._build_state()

    def reset(self, initial_price: float) -> None:
        """Re-initialise the filter with a new starting price.

        Resets state vector to [initial_price, 0.0], covariance matrix to
        diagonal [[initial_price_variance, 0], [0, initial_trend_variance]]
        using the configured initial variances, step counter to 0, innovation to 0.0,
        and Kalman gain to zeros.

        Parameters
        ----------
        initial_price : float
            New starting price. Must be positive and finite.

        Raises
        ------
        TypeError
            If *initial_price* is not numeric or is a boolean.
        ValueError
            If *initial_price* is NaN, infinite, zero, or negative.
        """
        initial_price = _validate_price(initial_price, "initial_price")

        self._x = np.array([initial_price, 0.0], dtype=np.float64)
        self._P = np.array(
            [[self._initial_price_variance, 0.0],
             [0.0, self._initial_trend_variance]],
            dtype=np.float64,
        )

        self._innovation = 0.0
        self._kalman_gain = np.zeros((2, 1), dtype=np.float64)
        self._step = 0

    @property
    def step_count(self) -> int:
        """Number of update steps performed since construction or last reset."""
        return self._step

    # ---- private helpers ----------------------------------------------------

    def _build_state(self) -> KalmanState:
        """Construct an immutable `KalmanState` from internal arrays."""
        price_var = float(self._P[0, 0])
        trend_var = float(self._P[1, 1])

        return KalmanState(
            estimated_price=float(self._x[0]),
            trend=float(self._x[1]),
            uncertainty=math.sqrt(max(price_var, 0.0)),
            trend_uncertainty=math.sqrt(max(trend_var, 0.0)),
            price_variance=price_var,
            trend_variance=trend_var,
            innovation=self._innovation,
            kalman_gain_price=float(self._kalman_gain[0, 0]),
        )


# ---------------------------------------------------------------------------
# Demonstration
# ---------------------------------------------------------------------------

def _run_demo() -> None:
    """Run a short synthetic demonstration of the Kalman filter.

    Generates a price series with a known linear trend plus Gaussian noise.
    Initializes the filter with the first observation, displays its initial state,
    and then feeds subsequent observations into update().

    This demonstration does NOT connect to any trading API or execution
    system. It is purely analytical and deterministic.
    """
    np.random.seed(42)

    # Synthetic parameters
    true_price_start = 100.0
    true_trend = 0.5          # $/step
    noise_std = 2.0           # observation noise
    n_steps = 30

    # Generate true prices and noisy observations
    true_prices: List[float] = []
    observed_prices: List[float] = []
    for i in range(n_steps):
        true_p = true_price_start + true_trend * i
        obs_p = true_p + np.random.normal(0, noise_std)
        # Ensure observation stays positive for validity
        obs_p = max(obs_p, 0.01)
        true_prices.append(true_p)
        observed_prices.append(obs_p)

    # Initialise filter with the first observation
    kf = KalmanFilter(
        observed_prices[0],
        dt=1.0,
        process_noise_price=0.1,
        process_noise_trend=0.01,
        measurement_noise=noise_std ** 2,
    )

    # Header
    print()
    print("=" * 90)
    print("  X Quant X  —  Kalman Filter Demonstration (synthetic data)")
    print("=" * 90)
    print(
        f"{'Step':>4}  {'True':>9}  {'Observed':>9}  {'Estimated':>9}  "
        f"{'Trend':>8}  {'Uncert.':>8}  {'Innov.':>8}  {'K_price':>8}"
    )
    print("-" * 90)

    # Display initial state at step 0 (before updates)
    init_state = kf.get_state()
    print(
        f"{0:4d}  {true_prices[0]:9.3f}  {observed_prices[0]:9.3f}  "
        f"{init_state.estimated_price:9.3f}  {init_state.trend:8.4f}  "
        f"{init_state.uncertainty:8.4f}  {init_state.innovation:8.3f}  "
        f"{init_state.kalman_gain_price:8.4f}"
    )

    # Feed subsequent observations (observed_prices[1:])
    for i in range(1, n_steps):
        obs = observed_prices[i]
        state = kf.update(obs)
        print(
            f"{i:4d}  {true_prices[i]:9.3f}  {obs:9.3f}  "
            f"{state.estimated_price:9.3f}  {state.trend:8.4f}  "
            f"{state.uncertainty:8.4f}  {state.innovation:8.3f}  "
            f"{state.kalman_gain_price:8.4f}"
        )

    last_state = kf.get_state()
    print("-" * 90)
    print(f"  Final state  — price: {last_state.estimated_price:.3f}, "
          f"trend: {last_state.trend:.4f}, uncertainty: {last_state.uncertainty:.4f}")
    print(f"  Steps processed (update calls): {kf.step_count}")
    print("=" * 90)
    print()


if __name__ == "__main__":
    _run_demo()
