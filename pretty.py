"""
Print one game as a readable story, for the Sunday-night "could a human solve
this?" check. Public events first; true roles only at the very bottom.
"""

from __future__ import annotations

from .state import GameRecord


def game_to_text(rec: GameRecord, reveal: bool = True) -> str:
    pub, sec = rec.public, rec.secret
    lines = [f"=== Game (seed {sec.seed}) ==="]

    for r in range(1, pub.round + 1):
        lines.append(f"\n--- Round {r} ---")
        for e in pub.eliminations:
            if e.round == r and e.cause == "night":
                lines.append(f"Night: Player {e.player} was killed ({e.revealed_role}).")

        accs = [a for a in pub.accusations if a.round == r]
        for a in accs:
            lines.append(f"  Player {a.accuser} accuses Player {a.target}")

        votes = [v for v in pub.votes if v.round == r]
        for v in votes:
            lines.append(f"  Player {v.voter} votes for Player {v.target}")

        for e in pub.eliminations:
            if e.round == r and e.cause == "vote":
                lines.append(f"Day: Player {e.player} was voted out. "
                             f"They were {e.revealed_role.upper()}.")

    if reveal:
        lines.append("\n=== Answer key (secret) ===")
        imps = [i for i, role in enumerate(sec.true_roles) if role == "impostor"]
        lines.append(f"Impostors: Players {imps[0]} and {imps[1]}")
        lines.append(f"Winner: {sec.winner}")
        lines.append("Seats: " + ", ".join(f"{i}={t}" for i, t in enumerate(sec.bot_types)))
    return "\n".join(lines)
