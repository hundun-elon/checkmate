# RBC Bot Arena

This repository contains multiple ReconChess bots and helper scripts to run matches and tournaments between them.

## Bots

Located in the src/ directory:

* random_sensing_bot.py
* troutbot.py
* improvedbot.py

Additionally, the built-in reconchess.bots.random_bot is used as a standard opponent.

## Script: run_match.sh

This script allows you to run a single match between two bots of your choosing.

Prompts you to select:

* Your bot
* An opponent bot
* Which color you want to play (White or Black)

Runs the match using rc-bot-match

## Script: tournament.sh

This script runs a round-robin tournament between all listed bots.

Each bot plays against every other bot twice:

* Once as White
* Once as Black

Automatically iterates over all matchups using rc-bot-match