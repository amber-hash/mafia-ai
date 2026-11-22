"""
Run one game and print it as a story.

    python demo.py --seed 42
    python demo.py --seed 42 --hide-roles     # try to solve it yourself first
"""

import argparse

from mafia.engine import play_game
from mafia.pretty import game_to_text
from mafia.stand_in_bots import stand_in_factory  # swap for B's bots later


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--hide-roles", action="store_true")
    args = ap.parse_args()

    record = play_game(args.seed, stand_in_factory)
    print(game_to_text(record, reveal=not args.hide_roles))


if __name__ == "__main__":
    main()
