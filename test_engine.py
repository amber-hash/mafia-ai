"""
One test (or a few) per "Done when" line in Student A's tasks.
Run with:  python -m pytest -q
"""

import json
import random

import pytest

from mafia.engine import (
    MAX_ROUNDS, N_IMPOSTORS, N_PLAYERS, BotError, Game, RoundCapExceeded,
    assign_roles, check_winner, partner_of, play_game, tally_votes,
)
from mafia.state import GameRecord, Vote
from mafia.stand_in_bots import StandInRandomBot, stand_in_factory


# --- Task 1: roles -------------------------------------------------------------

def test_roles_have_two_impostors():
    roles = assign_roles(random.Random(1))
    assert len(roles) == N_PLAYERS
    assert roles.count("impostor") == N_IMPOSTORS


def test_roles_differ_across_seeds():
    deals = {assign_roles(random.Random(s)) for s in range(50)}
    assert len(deals) > 10


def test_impostors_know_each_other_innocents_know_nothing():
    roles = assign_roles(random.Random(7))
    a, b = [i for i, r in enumerate(roles) if r == "impostor"]
    assert partner_of(a, roles) == b and partner_of(b, roles) == a
    for i, r in enumerate(roles):
        if r == "innocent":
            assert partner_of(i, roles) is None


# --- Task 2: night ---------------------------------------------------------------

def test_night_kills_one_living_innocent():
    g = Game(3, stand_in_factory)
    g.round = 1
    victim = g.night()
    assert g.roles[victim] == "innocent"
    assert victim not in g.alive
    assert g.eliminations[-1].cause == "night"
    assert g.eliminations[-1].revealed_role == "innocent"


# --- Task 3: day / vote counting -----------------------------------------------

def test_tally_clear_winner():
    votes = [Vote(1, 0, 5), Vote(1, 1, 5), Vote(1, 2, 3)]
    assert tally_votes(votes, random.Random(0)) == 5


def test_tally_tie_picks_one_of_the_tied_and_is_seeded():
    votes = [Vote(1, 0, 5), Vote(1, 1, 3), Vote(1, 2, 7)]
    picks = {tally_votes(votes, random.Random(s)) for s in range(40)}
    assert picks <= {3, 5, 7} and len(picks) > 1
    assert tally_votes(votes, random.Random(9)) == tally_votes(votes, random.Random(9))


def test_vote_reveals_role():
    g = Game(5, stand_in_factory)
    g.round = 1
    g.night()
    g.accusation_phase()
    _, out = g.voting_phase()
    assert g.eliminations[-1].player == out
    assert g.eliminations[-1].revealed_role == g.roles[out]


# --- Task 4: win conditions ------------------------------------------------------

ROLES = ("impostor", "impostor", "innocent", "innocent",
         "innocent", "innocent", "innocent", "innocent")

def test_innocents_win_when_impostors_gone():
    assert check_winner([2, 3, 4], ROLES) == "innocents"

def test_impostors_win_at_parity():
    assert check_winner([0, 1, 2, 3], ROLES) == "impostors"   # 2 vs 2
    assert check_winner([0, 2], ROLES) == "impostors"         # 1 vs 1

def test_game_continues():
    assert check_winner([0, 1, 2, 3, 4], ROLES) is None       # 2 vs 3
    assert check_winner(list(range(8)), ROLES) is None


# --- Task 5: full game + round cap ---------------------------------------------

def test_full_games_finish_and_are_valid():
    for seed in range(500):
        rec = play_game(seed, stand_in_factory)   # invariants asserted inside
        assert rec.secret.winner in ("impostors", "innocents")
        assert rec.public.round <= MAX_ROUNDS


def test_round_cap_raises(monkeypatch):
    # Fake a bug: deaths never end the game.
    monkeypatch.setattr("mafia.engine.check_winner", lambda alive, roles: None)
    class Immortal(Game):
        def _eliminate(self, player, cause):   # nobody actually dies
            pass
    with pytest.raises(RoundCapExceeded):
        Immortal(1, stand_in_factory).play()


# --- Task 6: determinism ---------------------------------------------------------

def test_same_seed_same_game_byte_for_byte():
    a = json.dumps(play_game(42, stand_in_factory).to_dict())
    b = json.dumps(play_game(42, stand_in_factory).to_dict())
    assert a == b


def test_different_seeds_differ():
    a = json.dumps(play_game(42, stand_in_factory).to_dict())
    b = json.dumps(play_game(43, stand_in_factory).to_dict())
    assert a != b


# --- Bad bots must crash loudly (spec section 6) ------------------------------

class SelfVoter(StandInRandomBot):
    def vote(self, view):
        return self.id

class DeadVoter(StandInRandomBot):
    def vote(self, view):
        dead = [e.player for e in view.public.eliminations]
        return dead[0]

class NoneVoter(StandInRandomBot):
    def vote(self, view):
        return None

@pytest.mark.parametrize("bad", [SelfVoter, DeadVoter, NoneVoter])
def test_illegal_votes_raise(bad):
    with pytest.raises(BotError):
        play_game(0, lambda pid, imp, partner, rng: bad(pid, imp, partner, rng))


# --- The two piles stay separate -------------------------------------------------

def test_public_record_has_no_secret_fields():
    pub = play_game(1, stand_in_factory).public.to_dict()
    assert set(pub) == {"alive", "round", "votes", "accusations", "eliminations"}


def test_record_round_trips_through_json():
    rec = play_game(11, stand_in_factory)
    again = GameRecord.from_dict(json.loads(json.dumps(rec.to_dict())))
    assert again == rec


def test_wrong_schema_is_a_clear_error():
    d = play_game(11, stand_in_factory).to_dict()
    d["schema"] = 99
    with pytest.raises(ValueError, match="schema"):
        GameRecord.from_dict(d)
