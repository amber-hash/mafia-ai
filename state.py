"""
Data structures shared by the engine (Student A) and the bots (Student B).

The single most important idea in this file: there are TWO piles of information.

  PublicState  - what any outside observer could see. The AI reads ONLY this.
  SecretTruth  - everyone's real role, the seed, the winner. Used only for scoring.

They are separate classes on purpose. The inference agent's function should take
a PublicState and nothing else, so it physically cannot reach true_roles.

Everything bots receive is frozen (immutable tuples, frozen dataclasses), so a
buggy bot can't accidentally edit the game history.

Player ids are 0..7 everywhere. Never 1..8.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, NamedTuple, Optional

SCHEMA_VERSION = 1

Role = Literal["impostor", "innocent"]
Cause = Literal["night", "vote"]
Winner = Literal["impostors", "innocents"]

IMPOSTOR: Role = "impostor"
INNOCENT: Role = "innocent"


# --- Single events ------------------------------------------------------------
# NamedTuples so you can write v.voter instead of v[1], but they still behave
# like plain tuples (and turn into JSON lists).

class Vote(NamedTuple):
    round: int
    voter: int
    target: int


class Accusation(NamedTuple):
    round: int
    accuser: int
    target: int


class Elimination(NamedTuple):
    round: int
    player: int
    cause: Cause            # "night" or "vote"
    revealed_role: Role     # announced publicly the moment they leave


# --- The public pile ----------------------------------------------------------

@dataclass(frozen=True)
class PublicState:
    alive: tuple[int, ...]
    round: int
    votes: tuple[Vote, ...]
    accusations: tuple[Accusation, ...]
    eliminations: tuple[Elimination, ...]

    def to_dict(self) -> dict:
        return {
            "alive": list(self.alive),
            "round": self.round,
            "votes": [list(v) for v in self.votes],
            "accusations": [list(a) for a in self.accusations],
            "eliminations": [list(e) for e in self.eliminations],
        }

    @staticmethod
    def from_dict(d: dict) -> "PublicState":
        return PublicState(
            alive=tuple(d["alive"]),
            round=d["round"],
            votes=tuple(Vote(*v) for v in d["votes"]),
            accusations=tuple(Accusation(*a) for a in d["accusations"]),
            eliminations=tuple(Elimination(*e) for e in d["eliminations"]),
        )


# --- What one bot gets to see -------------------------------------------------

@dataclass(frozen=True)
class PlayerView:
    id: int                     # which player am I
    is_impostor: bool
    partner: Optional[int]      # the other impostor's id, or None if innocent
    public: PublicState


# --- The secret pile ----------------------------------------------------------

@dataclass(frozen=True)
class SecretTruth:
    true_roles: tuple[Role, ...]    # true_roles[i] is player i's real role
    seed: int
    winner: Winner
    bot_types: tuple[str, ...]      # which personality sat in each seat

    def to_dict(self) -> dict:
        return {
            "true_roles": list(self.true_roles),
            "seed": self.seed,
            "winner": self.winner,
            "bot_types": list(self.bot_types),
        }

    @staticmethod
    def from_dict(d: dict) -> "SecretTruth":
        return SecretTruth(
            true_roles=tuple(d["true_roles"]),
            seed=d["seed"],
            winner=d["winner"],
            bot_types=tuple(d["bot_types"]),
        )


# --- A finished game ----------------------------------------------------------

@dataclass(frozen=True)
class GameRecord:
    """A finished game. Keeps the two piles side by side but never merged.

    When the AI is evaluated, hand it record.public and keep record.secret
    for the answer key.
    """
    public: PublicState
    secret: SecretTruth

    def to_dict(self) -> dict:
        # Student B's save/load code should use these two methods.
        return {
            "schema": SCHEMA_VERSION,
            "public": self.public.to_dict(),
            "secret": self.secret.to_dict(),
        }

    @staticmethod
    def from_dict(d: dict) -> "GameRecord":
        if d.get("schema") != SCHEMA_VERSION:
            raise ValueError(
                f"Saved game has schema {d.get('schema')!r}, "
                f"this code expects {SCHEMA_VERSION}. Regenerate the file."
            )
        return GameRecord(
            public=PublicState.from_dict(d["public"]),
            secret=SecretTruth.from_dict(d["secret"]),
        )
