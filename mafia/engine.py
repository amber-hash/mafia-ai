"""
The Referee (Student A).

Runs one game of Mafia from start to finish:

    round 1: night -> win check -> accusations -> votes -> elimination -> win check
    round 2: ...

The small pieces (assign_roles, tally_votes, check_winner) are plain functions so
you can test each one by hand. The Game class glues them together.

Randomness rule: ONE random.Random(seed) per game, created in Game.__init__ and
passed to everything that needs randomness, including the bots. Never call
random.choice() / random.random() at module level anywhere in the project.
"""

from __future__ import annotations

import random
from collections import Counter
from typing import Callable, Optional, Protocol, Sequence

from .state import (
    IMPOSTOR,
    INNOCENT,
    Accusation,
    Elimination,
    GameRecord,
    PlayerView,
    PublicState,
    Role,
    SecretTruth,
    Vote,
    Winner,
)

N_PLAYERS = 8
N_IMPOSTORS = 2
MAX_ROUNDS = 20


# --- Errors -------------------------------------------------------------------

class BotError(Exception):
    """A bot returned something illegal (itself, a dead player, None for a vote...).

    We raise instead of quietly fixing it: a silent fix would hide a bug in the
    bot and change the behaviour the AI is supposed to learn.
    """


class RoundCapExceeded(RuntimeError):
    """The game ran past MAX_ROUNDS. With 8 players that can only be a bug."""


# --- The bot contract (Student B implements this) -----------------------------

class BotLike(Protocol):
    def accuse(self, view: PlayerView) -> Optional[int]: ...
    def vote(self, view: PlayerView) -> int: ...


# A bot factory builds the bot for one seat. The engine hands it the seat number,
# the player's private info, and the game's shared random generator.
#   factory(player_id, is_impostor, partner, rng) -> bot
BotFactory = Callable[[int, bool, Optional[int], random.Random], BotLike]


# --- Task 1: deal out the roles -----------------------------------------------

def assign_roles(rng: random.Random,
                 n_players: int = N_PLAYERS,
                 n_impostors: int = N_IMPOSTORS) -> tuple[Role, ...]:
    """Secretly pick n_impostors players. Returns roles[i] for each player i."""
    impostors = set(rng.sample(range(n_players), n_impostors))
    return tuple(IMPOSTOR if i in impostors else INNOCENT for i in range(n_players))


def partner_of(player: int, roles: Sequence[Role]) -> Optional[int]:
    """The other impostor's id if `player` is an impostor, else None.

    This is the ONLY private information anyone ever gets.
    """
    if roles[player] != IMPOSTOR:
        return None
    return next(p for p, r in enumerate(roles) if r == IMPOSTOR and p != player)


# --- Task 3 (helper): count the votes -----------------------------------------

def tally_votes(round_votes: Sequence[Vote], rng: random.Random) -> int:
    """Return the player who is thrown out.

    Most votes wins. On a tie, pick one of the tied players at random using the
    game's generator. Someone is always eliminated.
    """
    if not round_votes:
        raise ValueError("No votes to count")
    counts = Counter(v.target for v in round_votes)
    top = max(counts.values())
    tied = sorted(p for p, c in counts.items() if c == top)  # sorted -> deterministic
    return tied[0] if len(tied) == 1 else rng.choice(tied)


# --- Task 4: is the game over? -------------------------------------------------

def check_winner(alive: Sequence[int], roles: Sequence[Role]) -> Optional[Winner]:
    """Run after EVERY death.

    Innocents win when no impostors are left.
    Impostors win when living impostors >= living innocents.
    Otherwise None (keep playing).
    """
    imps = sum(1 for p in alive if roles[p] == IMPOSTOR)
    inns = len(alive) - imps
    if imps == 0:
        return "innocents"
    if imps >= inns:
        return "impostors"
    return None


# --- Tasks 2, 3, 5: the game itself -------------------------------------------

class Game:
    def __init__(self, seed: int, bot_factory: BotFactory):
        self.seed = seed
        self.rng = random.Random(seed)        # the ONE generator for this game

        # Secret pile (never shown to bots except each one's own role/partner)
        self.roles = assign_roles(self.rng)
        self.winner: Optional[Winner] = None

        # Public pile (kept as mutable lists here, frozen when handed out)
        self.alive: list[int] = list(range(N_PLAYERS))
        self.round = 0
        self.votes: list[Vote] = []
        self.accusations: list[Accusation] = []
        self.eliminations: list[Elimination] = []

        self.bots = [
            bot_factory(pid, self.roles[pid] == IMPOSTOR,
                        partner_of(pid, self.roles), self.rng)
            for pid in range(N_PLAYERS)
        ]

    # --- views ----------------------------------------------------------------

    def public_state(self) -> PublicState:
        """A frozen snapshot of everything public, right now."""
        return PublicState(
            alive=tuple(self.alive),
            round=self.round,
            votes=tuple(self.votes),
            accusations=tuple(self.accusations),
            eliminations=tuple(self.eliminations),
        )

    def view_for(self, pid: int, public: PublicState) -> PlayerView:
        return PlayerView(
            id=pid,
            is_impostor=self.roles[pid] == IMPOSTOR,
            partner=partner_of(pid, self.roles),
            public=public,
        )

    # --- shared death handling -----------------------------------------------

    def _eliminate(self, player: int, cause: str) -> None:
        assert player in self.alive, f"Tried to kill {player}, who is already dead"
        self.alive.remove(player)
        # The role is revealed publicly the moment the player leaves.
        self.eliminations.append(
            Elimination(self.round, player, cause, self.roles[player])
        )
        self.winner = check_winner(self.alive, self.roles)

    # --- Task 2: night -------------------------------------------------------

    def night(self) -> int:
        """Impostors kill one living innocent, chosen uniformly at random."""
        targets = [p for p in self.alive if self.roles[p] == INNOCENT]
        victim = self.rng.choice(targets)
        self._eliminate(victim, "night")
        return victim

    # --- accusations ----------------------------------------------------------

    def accusation_phase(self) -> list[Accusation]:
        public = self.public_state()       # everyone sees the same snapshot
        made = []
        for pid in list(self.alive):
            target = self.bots[pid].accuse(self.view_for(pid, public))
            if target is None:
                continue
            self._check_target(pid, target, "accused")
            made.append(Accusation(self.round, pid, target))
        self.accusations.extend(made)
        return made

    # --- Task 3: day ---------------------------------------------------------

    def voting_phase(self) -> tuple[list[Vote], int]:
        """Everyone alive votes (simultaneously), then the top vote-getter is out."""
        public = self.public_state()       # includes this round's accusations
        round_votes = []
        for pid in list(self.alive):
            target = self.bots[pid].vote(self.view_for(pid, public))
            if target is None:
                raise BotError(f"Player {pid} returned None for vote; voting is mandatory")
            self._check_target(pid, target, "voted for")
            round_votes.append(Vote(self.round, pid, target))

        assert len(round_votes) == len(self.alive), "Vote count != living players"
        self.votes.extend(round_votes)

        out = tally_votes(round_votes, self.rng)
        self._eliminate(out, "vote")
        return round_votes, out

    def _check_target(self, pid: int, target, verb: str) -> None:
        bot = type(self.bots[pid]).__name__
        if not isinstance(target, int) or isinstance(target, bool):
            raise BotError(f"Player {pid} ({bot}) {verb} {target!r}, which is not a player id")
        if target == pid:
            raise BotError(f"Player {pid} ({bot}) {verb} themselves")
        if target not in self.alive:
            raise BotError(f"Player {pid} ({bot}) {verb} {target}, who is not alive")

    # --- Task 5: put it together ---------------------------------------------

    def play(self) -> GameRecord:
        while self.winner is None:
            self.round += 1
            if self.round > MAX_ROUNDS:
                raise RoundCapExceeded(f"Seed {self.seed} passed {MAX_ROUNDS} rounds")

            self.night()
            if self.winner:
                break

            self.accusation_phase()
            self.voting_phase()

        self._check_invariants()
        return GameRecord(
            public=self.public_state(),
            secret=SecretTruth(
                true_roles=self.roles,
                seed=self.seed,
                winner=self.winner,
                bot_types=tuple(type(b).__name__ for b in self.bots),
            ),
        )

    # --- invariants from section 6 of the spec --------------------------------

    def _check_invariants(self) -> None:
        dead = [e.player for e in self.eliminations]
        assert len(dead) == len(set(dead)), "Someone was eliminated twice"
        assert not set(dead) & set(self.alive), "A dead player is still in alive"
        assert set(dead) | set(self.alive) == set(range(N_PLAYERS)), "A player went missing"
        assert all(self.roles[e.player] == INNOCENT
                   for e in self.eliminations if e.cause == "night"), "Night killed an impostor"
        assert all(e.revealed_role == self.roles[e.player]
                   for e in self.eliminations), "Revealed role doesn't match true role"
        assert self.winner is not None, "Game ended without a winner"

        # Replay the deaths to check votes/accusations only ever targeted the living.
        alive = set(range(N_PLAYERS))
        for r in range(1, self.round + 1):
            for e in self.eliminations:
                if e.round == r and e.cause == "night":
                    alive.discard(e.player)
            r_votes = [v for v in self.votes if v.round == r]
            r_accs = [a for a in self.accusations if a.round == r]
            for v in r_votes:
                assert v.voter in alive and v.target in alive and v.voter != v.target
            for a in r_accs:
                assert a.accuser in alive and a.target in alive and a.accuser != a.target
            if r_votes:
                assert len(r_votes) == len(alive), f"Round {r}: wrong number of votes"
            for e in self.eliminations:
                if e.round == r and e.cause == "vote":
                    alive.discard(e.player)


def play_game(seed: int, bot_factory: BotFactory) -> GameRecord:
    """The one function the batch runner needs: seed in, finished game out."""
    return Game(seed, bot_factory).play()
