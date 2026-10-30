"""Search a recipe's doses for the most evil replies that stay coherent.

The search is coordinate-wise: each pass tries scaling each steer's dose
magnitude up and then down by ``step`` and moves to the first change that
scores better, keeping every sign fixed. A pass with no improvement halves
``step``. The search stops when ``step`` falls below ``min_step`` or after
``max_trials`` judged sweeps.

A trial is *feasible* when its mean judged coherence is at least
``min_coherence``. Feasible trials beat infeasible ones; among feasible
trials higher evil wins, then higher coherence; among infeasible trials
higher coherence wins, which walks the search back toward feasibility.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from evilqwen.steering import AnySteer
from evilqwen.sweep import Sweep, SweepResult


@dataclass(frozen=True)
class Trial:
    """One judged sweep of a recipe at specific doses."""

    result: SweepResult
    min_coherence: float

    @property
    def feasible(self) -> bool:
        return self.result.mean("coherence") >= self.min_coherence

    @property
    def rank(self) -> tuple[bool, float, float]:
        """Sort key under which a larger value is a better trial."""
        evil, coherence = self.result.mean("evil"), self.result.mean("coherence")
        return (self.feasible, evil if self.feasible else coherence, coherence)


class DoseSearch:
    """Coordinate search over the dose magnitudes of a fixed set of steers.

    ``record`` receives every new sweep result, and ``log`` one line per trial.
    Recipes are compared at doses rounded to three decimals, so a revisited
    dose combination reuses its earlier trial.
    """

    def __init__(
        self,
        sweep: Sweep,
        min_coherence: float,
        step: float,
        min_step: float,
        max_trials: int,
        record: Callable[[SweepResult], None],
        log: Callable[[str], None],
    ):
        if not 0 < min_step <= step < 1:
            raise ValueError("need 0 < min-step <= step < 1")
        if max_trials < 1:
            raise ValueError(f"need at least one trial, got {max_trials}")
        self.sweep = sweep
        self.min_coherence = min_coherence
        self.step = step
        self.min_step = min_step
        self.max_trials = max_trials
        self.record = record
        self.log = log
        self.trials: dict[tuple[AnySteer, ...], Trial] = {}

    @staticmethod
    def scaled(
        steers: tuple[AnySteer, ...], index: int, factor: float
    ) -> tuple[AnySteer, ...]:
        """``steers`` with steer ``index``'s dose multiplied by ``factor``."""
        changed = replace(steers[index], dose=round(steers[index].dose * factor, 3))
        return steers[:index] + (changed,) + steers[index + 1 :]

    def evaluate(self, steers: tuple[AnySteer, ...]) -> Trial:
        """Judge ``steers``, reusing an earlier trial of the same doses."""
        if steers in self.trials:
            return self.trials[steers]
        result = self.sweep.run(steers)
        self.record(result)
        trial = Trial(result, self.min_coherence)
        self.trials[steers] = trial
        self.log(
            f"trial {len(self.trials)}/{self.max_trials}: "
            f"evil {result.summary('evil')}  coherence {result.summary('coherence')}"
            f"  {result.name}"
        )
        return trial

    def run(self, start: tuple[AnySteer, ...]) -> Trial:
        """Search from ``start`` and return the best trial found."""
        if not start:
            raise ValueError("a dose search needs at least one steer")
        rounded = tuple(replace(s, dose=round(s.dose, 3)) for s in start)
        best = self.evaluate(rounded)
        step = self.step
        while step >= self.min_step and len(self.trials) < self.max_trials:
            improved = False
            for index in range(len(start)):
                for factor in (1 + step, 1 - step):
                    if len(self.trials) >= self.max_trials:
                        return best
                    trial = self.evaluate(
                        self.scaled(best.result.steers, index, factor)
                    )
                    if trial.rank > best.rank:
                        best = trial
                        improved = True
                        break
            if not improved:
                step /= 2
        return best
