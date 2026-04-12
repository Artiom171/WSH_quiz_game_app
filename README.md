# WSH_quiz_game_app
This is a web app, for my self-made Who's smart here? quiz game

This web app is created with a lof of hepling from various AI 

# How the app should be used?

During a Who's Smart Here? quiz game, the player opens the web app
The first page - is a registration page, that consists of a name input field and a Submit button
Player enters his name and presses Submit, after what is redirected to the first questions page
The question page is the same one throught the whole game, the number of the questions and the round increases only
The page consists of the number of the question, number of the round, answer input field and a Submit button
The player enters the answer and presses Submit, by what the answer is sent ot the answers db with a appropriate number of the question, number of the round and the name of the player
The answers table is shown on the answers page for the game host 
The game host must check, wheter the answer is correct or not and mark the correctness of the answer by clicking on the check mark or the cross
If the answer is marked correct - the amount of final amount of points of the particular player is increased by one
If the answer is marked incorrect - nothing happens 
The final results table is shown on the final result page
All players are sorted by the amount of the final points (from the most, to least points)
