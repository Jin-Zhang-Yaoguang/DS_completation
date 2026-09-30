# Kaggriculture: 95.5% Win Rate by Routing Between Public Replays
## One opening, three schedules, and why the splice point decides everything

Fixed replays are strong in this competition but they are blind. The town unlocks a
different set of shops on every seed, and a schedule that farms wool is wasted when no
yarn store ever opens.

This notebook is my router. It plays one opening for six days, reads the market and the
town, then commits to a different public schedule for the rest of the season.

Result over 44,096 games against 689 replays it never trained on, 32 seeds, both seats:

> one fixed replay played to the buzzer: **84.6%**
>
> this router: **95.5%**

My previous version scored 93.8% on exactly the same games.

## The part that took me longest to see

The whole thing rest on one property of the public replays.

A schedule that takes over at day six inherits a farm it did not build. If it wants to
harvest a tile and nobody planted there, the turn is thrown away. So I hashed the worker
actions of the first six days of every replay in my corpus and grouped them.

623 distinct openings. One of them covers 1,520 replays, which is 36 percent of everything
I have.

Inside that group a splice is safe, because every member walked its workers over the same
tiles in the same order. Outside of it you are gambling. The strongest single replay in my
corpus wins 90.8 percent on its own and sits in a group of size one, so it can never route
anywhere at all. I burned two builds on it before I checked.

## The decision

At turn 144 the agent reads the public informations and picks:

* town demands wool, go to the sheep schedule
* else town demands milk, go to the cow schedule
* else stay on the opening

That is the whole main switch. Five embedded schedules, nine decision nodes, no online
search, 0.016 ms per turn at p99.

## The agent

The cell below writes main.py. Standard library only, no external packages.

## A full match in the official environment

720 turns, the agent against itself, to prove it loads and finishes clean.

## Build submission.tar.gz

## What I would tell my past self

1. Group your replays by their opening before you rank them by strength. A strong replay
with no family is a dead end.
2. Measure the switch, not the tape. The opening alone is worth 84.6 percent and the
switch adds eleven points on top.
3. Freeze before you touch your test set. I did not tuned anything after the freeze, and
two ideas that looked good on validation came out flat.

Upvote if this was useful, and good luck out there.
