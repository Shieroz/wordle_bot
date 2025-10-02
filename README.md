# wordle_bot
Yet another wordle bot

### Dependencies
This script only relies on pyautogui for controlling mouse and keyboard. Everything else are standard libraries in any modern python installation.

### Instructions
Before running the script, take a screenshot of the game window and crop out the guess area like below, then change the ```GUESSES_PNG``` variable to point to that file.

![Guess area](guesses.png)

When it's time to run the script, make sure that no other image similar looking to the guess area is presented, otherwise pyautogui will mistook that for the game screen and fail.

Note: If ```LAST_MILE``` is set to True, if there are only ```N_LAST_MILE``` or less number of valid answers left, the app will ask if the user wants to continue finishing the puzzle themselves and giving a list of all valid guesses. Pressing ```Y``` will let the app continue by itself while ```N``` will quit the app.
