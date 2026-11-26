#player 3 is innocent, 6 people are alive, last round3 people voted for 7, 2 voted for 3, players 5 and 7 accused me
#accusing is optional so only 3/6 spoke up, quiet players stay quiet
#alive is present, votes are from previous round, accusations are from previous round, round is current round
#
import random

from mafia.state import PlayerView, PublicState, Vote, Accusation, Elimination
from mafia.players import (
    Bot, RandomBot, NaiveBot, BandwagonerBot, GrudgeHolderBot, QuietBot,
)


situation = PlayerView(
    id=2,
    is_impostor=False,
    partner=None,
    public=PublicState(
        alive=(0, 1, 2, 4, 6, 7),
        round=2,
        votes=(
            Vote(1, 0, 5), Vote(1, 1, 5), Vote(1, 2, 5), Vote(1, 4, 0),
            Vote(1, 5, 2), Vote(1, 6, 0), Vote(1, 7, 5),
        ),
        accusations=(
            Accusation(1, 0, 6), Accusation(1, 1, 6),
            Accusation(1, 4, 7), Accusation(1, 7, 2),
        ),
        eliminations=(
            Elimination(1, 3, "night", "innocent"),
            Elimination(1, 5, "vote", "innocent"),
        ),
    ),
)

"""
bot = NaiveBot(random.Random(1))   # make a bot with a seeded random generator
choice = bot.vote(situation)                 # run vote() on your test situation
print(f"NaiveBot voted for player {choice}")
"""

def test_naive_votes_most_accused():
    assert NaiveBot(random.Random(1)).vote(situation) == 6


def test_bandwagoner_follows_last_round():
    assert BandwagonerBot(random.Random(1)).vote(situation) == 0


def test_grudge_holder_targets_accuser():
    assert GrudgeHolderBot(random.Random(1)).vote(situation) == 7

#test_partner_protection

class PartnerTargeter(Bot):
    """A test bot whose rule ALWAYS picks the partner, so protectPartner is the only thing deciding."""
    def vote(self, view):
        target = view.partner
        return self.protectPartner(view, target)


def make_view(is_impostor):
    return PlayerView(
        id=3,
        is_impostor=is_impostor,
        partner=5 if is_impostor else None,
        public=PublicState(alive=(0, 1, 3, 5, 6, 7), round = 2, votes=(), accusations=(), eliminations=()),
    )


def test_impostor_protects_partner():
    bot = PartnerTargeter(random.Random(1))  # ONE bot, reused, so the rng advances each call
    view = make_view(is_impostor=True)

    results = [bot.vote(view) for _ in range(100)]
    partner_count = results.count(5)

    print(f"partner returned {partner_count}/100 times (expected ~15)")
    assert 5 <= partner_count <= 30
    assert 3 not in results  # never votes for self
    assert all(r in [0, 1, 3, 5, 6, 7] for r in results)


def test_innocent_is_never_redirected():
    bot = Bot(random.Random(1))
    view = make_view(is_impostor=False)
    assert bot.protectPartner(view, 7) == 7

