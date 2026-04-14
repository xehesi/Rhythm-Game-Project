from core.game_logger import get_logger

logger = get_logger("Player")


class Player:
    MAX_HEALTH = 100
    HEALTH_PENALTY = 10
    MULTIPLIER_THRESHOLDS = [10, 30, 60]  # streak counts that raise multiplier

    # Timing windows (ms)
    PERFECT_WINDOW = 20
    GOOD_WINDOW = 50
    OK_WINDOW = 100

    # Base points per grade
    POINTS = {"perfect": 300, "good": 200, "ok": 100, "miss": 0}

    def __init__(self, assist_mode: bool = False):
        self.score: int = 0
        self.streak: int = 0
        self.multiplier: int = 1
        self.health: float = self.MAX_HEALTH
        self.assist_mode = assist_mode

        self.perfects = 0
        self.goods = 0
        self.oks = 0
        self.misses = 0

    def judge(self, error_ms: float) -> str:
        abs_err = abs(error_ms)
        if abs_err <= self.PERFECT_WINDOW:
            grade = "perfect"
            self.perfects += 1
        elif abs_err <= self.GOOD_WINDOW:
            grade = "good"
            self.goods += 1
        elif abs_err <= self.OK_WINDOW:
            grade = "ok"
            self.oks += 1
        else:
            grade = "miss"
            self.misses += 1

        if grade != "miss":
            self.streak += 1
            self._recalc_multiplier()
            self.score += self.POINTS[grade] * self.multiplier
            logger.debug(
                "HIT  grade=%s  err=%.1fms  streak=%d  mult=%d  score=%d",
                grade, error_ms, self.streak, self.multiplier, self.score,
            )
        else:
            self.streak = 0
            self.multiplier = 1
            if not self.assist_mode:
                self.health = max(0, self.health - self.HEALTH_PENALTY)
            logger.debug("MISS err=%.1fms  health=%.0f", error_ms, self.health)

        return grade

    def register_miss(self):
        """Called when a note passes the miss window without any input."""
        self.misses += 1
        self.streak = 0
        self.multiplier = 1
        if not self.assist_mode:
            self.health = max(0, self.health - self.HEALTH_PENALTY)
        logger.debug("AUTO-MISS  health=%.0f", self.health)

    @property
    def is_dead(self) -> bool:
        return self.health <= 0 and not self.assist_mode

    def _recalc_multiplier(self):
        m = 1
        for threshold in self.MULTIPLIER_THRESHOLDS:
            if self.streak >= threshold:
                m += 1
        self.multiplier = m
