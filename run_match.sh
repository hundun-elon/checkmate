#!/bin/bash

set -e

# List available bots
USER_BOTS=("./src/random_sensing_bot.py" "./src/troutbot.py" "reconchess.bots.random_bot" ./src/improvedbot.py)
OPPONENT_BOTS=("./src/random_sensing_bot.py" "./src/troutbot.py" "reconchess.bots.random_bot" ./src/improvedbot.py)

echo "Select your bot:"
select USER_BOT in "${USER_BOTS[@]}"; do
    if [[ -n "$USER_BOT" ]]; then
        break
    else
        echo "Invalid selection. Try again."
    fi
done

echo "Select opponent bot:"
select OPPONENT_BOT in "${OPPONENT_BOTS[@]}"; do
    if [[ -n "$OPPONENT_BOT" ]]; then
        break
    else
        echo "Invalid selection. Try again."
    fi
done

echo "Choose your color:"
select COLOR in "White" "Black"; do
    case $COLOR in
        White)
            echo "Running match: $USER_BOT (White) vs $OPPONENT_BOT (Black)"
            rc-bot-match "$USER_BOT" "$OPPONENT_BOT"
            break
            ;;
        Black)
            echo "Running match: $OPPONENT_BOT (White) vs $USER_BOT (Black)"
            rc-bot-match "$OPPONENT_BOT" "$USER_BOT"
            break
            ;;
        *)
            echo "Invalid selection. Try again."
            ;;
    esac
done
