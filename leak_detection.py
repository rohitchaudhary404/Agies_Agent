import math


class LeakDetectionEngine:
    """Flags a slot whose pass rate is improbably high for its baseline.

    The decision boundary is the exact one-sided binomial tail of the observed
    pass count under the baseline rate. For a fixed slot size this is the same
    boundary a Bernoulli CUSUM ends on, but the false-alarm rate is exact
    instead of depending on hand-tuned k/h constants.
    """

    ALPHA = 0.02
    MIN_RESPONSES = 20

    def __init__(self, db_manager, ai_gateway):
        self.db = db_manager
        self.ai = ai_gateway

    def run_statistical_cusum(self, item_id: str, baseline_p: float, recent_responses: list) -> bool:
        n = len(recent_responses)
        if n < self.MIN_RESPONSES:
            return False
        p0 = min(max(float(baseline_p), 0.01), 0.99)
        correct = sum(1 for response in recent_responses if response)
        return self.binomial_sf(correct, n, p0) < self.ALPHA

    @staticmethod
    def binomial_sf(k: int, n: int, p: float) -> float:
        """Exact P(X >= k) for X ~ Binomial(n, p)."""
        if k <= 0:
            return 1.0
        if k > n:
            return 0.0
        log_p, log_q = math.log(p), math.log1p(-p)
        log_n_fact = math.lgamma(n + 1)
        total = 0.0
        for i in range(k, n + 1):
            log_term = (
                log_n_fact - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                + i * log_p + (n - i) * log_q
            )
            total += math.exp(log_term)
        return min(total, 1.0)
