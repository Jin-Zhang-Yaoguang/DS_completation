# Shop Router 0908

## What kind of agent is this?

This agent does not plan every move from scratch while the game is running. Instead, it mainly follows a complete action plan prepared in advance. We call such a plan a **tape**: a recorded sequence of actions that can be replayed from the beginning to the end of the game.

The agent has several tapes and can switch between them using information that is already visible in the game. It checks the situation at only two points:

- At the start of Day 6, it checks whether a Yarn Store has appeared.
- At the start of Day 27, it checks how many eggs remain in the public market.

If a Yarn Store appears early, the agent switches to a tape that performed better under that condition. Near the end of the game, it chooses between two slightly different selling plans based on the egg supply.

The agent never uses the opponent's identity, the game seed, future shops, future outcomes, or any other hidden information.

## How was it created?

We started from publicly available match histories. Each history was converted into a tape by recording the agent's actions in order. We then treated these historical agents as if they would repeat the same tape in other games.

The submitted agent is not a direct copy of one player's history. We collected 1,326 public histories and found 1,313 unique action sequences. Strong one-day and three-day sections were taken from different histories and combined like pieces of a mosaic.

We explored and tested many possible combinations of these sections. We then looked for situations in which the main tape performed poorly. This led to the Yarn Store branch on Day 6. Finally, we tested small changes to selling quantities and timing. About 21 million candidate-game comparisons were used in the last refinement stage.

Candidates were tested against different opponents, random seeds, shop patterns, and from both player positions. The final choice was also tested on a separate set of games that was not used to select it. Its complete 719-action behavior was checked against the official game engine.

## Important limitation

There is an important limitation to this method.

For simulation, public match histories are converted into tapes, and the recorded opponents are assumed to repeat those tapes exactly. This makes large-scale testing possible, but it is only an approximation of a real match.

A tape always performs the same recorded actions. A real agent may instead react to shops, prices, its farm, or the actions of its opponent. More adaptive, non-tape agents have recently become common. Against such agents, replaying their old match histories as fixed tapes is not a complete simulation of how they would actually behave.

Therefore, strong results against the tape-based test set do not guarantee the same improvement against hidden leaderboard agents. The simulations are useful stress tests and comparison tools, but they are not a perfect model of the current competition.
