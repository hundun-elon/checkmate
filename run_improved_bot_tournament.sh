#!/bin/bash

# List of all bots
bots=(
  "./src/improvedbot.py"
  "./src/improvedbot3.py"
  "./src/improvedbot4.py"
  "./src/improvedbot5.py"
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
