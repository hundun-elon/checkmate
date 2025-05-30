#!/bin/bash

# List of all bots
bots=(
  "./src/random_sensing_bot.py"
  "./src/troutbot.py"
  "reconchess.bots.random_bot"
  "./src/improvedbot.py"
)

# Run each match in both directions (White vs Black and vice versa)
for ((i=0; i<${#bots[@]}; i++)); do
  for ((j=i+1; j<${#bots[@]}; j++)); do
    white=${bots[i]}
    black=${bots[j]}
    echo "Match: $white vs $black"
    rc-bot-match "$white" "$black"
    echo "Match: $black vs $white"
    rc-bot-match "$black" "$white"
  done
done
