"""
TEMPORARY stand-in bots so the engine can run before Student B's bots exist.

Delete this file (or stop importing it) once B's real bots are plugged in.
These deliberately have no personality and no partner protection.
"""

from __future__ import annotations

import random
from typing import Optional

from .state import PlayerView


class StandInRandomBot:
    def __init__(self, player_id: int, is_impostor: bool,
                 partner: Optional[int], rng: random.Random):
        self.id = player_id
        self.rng = rng

    def _others(self, view: PlayerView) -> list[int]:
        return [p for p in view.public.alive if p != self.id]

    def accuse(self, view: PlayerView) -> Optional[int]:
        # Accuse someone half the time, stay silent otherwise.
        return self.rng.choice(self._others(view)) if self.rng.random() < 0.5 else None

    def vote(self, view: PlayerView) -> int:
        return self.rng.choice(self._others(view))


def stand_in_factory(player_id, is_impostor, partner, rng):
    return StandInRandomBot(player_id, is_impostor, partner, rng)
