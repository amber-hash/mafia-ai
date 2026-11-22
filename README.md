# Mafia AI: Week 1 (Referee)

```
mafia/state.py          shared data structures (PublicState, PlayerView, SecretTruth, GameRecord)
mafia/engine.py         the referee (Student A)
mafia/pretty.py         prints one game as a readable story
mafia/stand_in_bots.py  TEMPORARY random bots until Student B's bots exist
demo.py                 python demo.py --seed 42 [--hide-roles]
tests/test_engine.py    python -m pytest -q
```

## Decisions taken (from the spec)
- Players are numbered **0–7**.
- Each round goes night, win check, accusations, votes, elimination, win check.
- Ties are broken at random with the game's seeded generator.
- The night target is a uniformly random living innocent.
- A bot that returns itself, a dead player or None for a vote raises `BotError`.
- Going past 20 rounds raises `RoundCapExceeded`.

## For Student B: how to plug in
The engine builds each bot through a factory:

```python
def factory(player_id: int, is_impostor: bool, partner: int | None, rng: random.Random) -> Bot
```

Use the `rng` you're given for all randomness. Never use the `random` module directly.
Pick each seat's personality inside the factory, also with `rng`.
Bots need `accuse(view) -> int | None` and `vote(view) -> int`.

- All bots vote on the same snapshot, so a bot can't see other votes from the current round.
- That snapshot does include the current round's accusations.

To save a game, use `json.dumps(record.to_dict())`. To load one, use `GameRecord.from_dict(json.loads(line))`.
The `"schema": 1` field is already included.

To run one game: `play_game(seed, factory) -> GameRecord`.
