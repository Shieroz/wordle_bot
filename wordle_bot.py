import requests, os, time, copy, random
import pyautogui as gui
from datetime import datetime

# ENV
UPDATE_FREQ = 7
ALLOWED_LIST_FILE = "wordle_allowed_guesses.txt"
ANSWER_LIST_FILE = "wordle_answers.txt"
#X_BUTTON_FILE = "x_button.png"
ALLOWED_LIST_URL = "https://gist.githubusercontent.com/cfreshman/cdcdf777450c5b5301e439061d29694c/raw/d7c9e02d45afd26e12a71b4564189a949c29e8a9/wordle-allowed-guesses.txt"
ANSWER_LIST_URL = "https://gist.githubusercontent.com/cfreshman/a03ef2cba789d8cf00c08f767e0fad7b/raw/c46f451920d5cf6326d550fb2d6abb1642717852/wordle-answers-alphabetical.txt"
GUESSES_PNG = "guesses.png"
#KEYBOARD_PNG = "keyboard.png"
GREEN = (107, 170, 100)
YELLOW = (200, 180, 88)
GRAY = (120, 124, 126)
TOPLEFT_OFFSET = 10
DEBUG = False
LAST_MILE = False # If there are only a few valid answers left, let the user do it themselves
N_LAST_MILE = 20

WORD_LENGTH = 5
TOTAL_GUESSES = 6
GUESSES = []
CORRECT_CHARS = {} # List of characters in the correct position - Green
PRESENT_CHARS = set() # List of characters in the word but wrong position - Yellow
INVALID_CHARS = set() # List of characters not in the word - Gray

# Global vars
answer_list = []
allowed_list = []

def update_lists():
    response = requests.get(ALLOWED_LIST_URL)
    with open(ALLOWED_LIST_FILE, "w") as f:
        f.write(response.text)

    response = requests.get(ANSWER_LIST_URL)
    with open(ANSWER_LIST_FILE, "w") as f:
        f.write(response.text)

def load_vocab():
    with open(ALLOWED_LIST_FILE, "r") as f:
        lines = f.readlines()
        allowed_list.extend([line[:-1] for line in lines])

    with open(ANSWER_LIST_FILE, "r") as f:
        lines = f.readlines()
        answer_list.extend([line[:-1] for line in lines])

def input_guess(guess: str = "adieu"):
    gui.write(guess, interval=0.1)
    gui.press('enter')
    print(f"GUESS {len(GUESSES)}: {guess.upper()}")
    GUESSES.append(guess)

def random_guess(pos_answers: list[str]):
    input_guess(pos_answers[random.randint(0, len(pos_answers)-1)])

if __name__=="__main__":
    # Update vocab from github and load into memory
    if not (os.path.exists(ALLOWED_LIST_FILE) and os.path.exists(ANSWER_LIST_FILE)):
        update_lists()
        print("Allowed or answer list missing, pulling fresh update.")
    else:
        with open(ANSWER_LIST_FILE, "r") as f:
            curr_datetime = datetime.now()
            mod_timestamp = os.path.getmtime(ANSWER_LIST_FILE)
            mod_datetime = datetime.fromtimestamp(mod_timestamp)
            time_diff = curr_datetime - mod_datetime
            if time_diff.days >= UPDATE_FREQ:
                update_lists()
                print(f"Lists are older than {UPDATE_FREQ} days, pulling fresh update")
    load_vocab()

    guess_area = gui.locateOnScreen(GUESSES_PNG)
    #keyboard_area = gui.locateOnScreen(KEYBOARD_PNG)
    print("Guess area: ", guess_area)
    #print("Keyboard area: ", keyboard_area)

    # Focus on play area
    guess_area_x, guess_area_y = gui.center(guess_area)
    gui.moveTo(guess_area_x, guess_area_y)
    gui.click()

    # Set up a set of possible answers
    pos_answers = copy.deepcopy(answer_list)

    # Block offsets
    offset_x = guess_area.width // 5
    offset_y = guess_area.height // 6
    top = guess_area.top
    left = guess_area.left

    while len(GUESSES) < TOTAL_GUESSES:
        if not GUESSES:
            # Choose a word for the initial guess, it should cover a large range of vowels to make subsequent guesses easier
            random_guess(pos_answers)
        else:
            # Eliminate words not matching new criteria
            # Take out any words not having all the green characters
            for char in CORRECT_CHARS.keys():
                pos_answers = [word for word in pos_answers if word[CORRECT_CHARS[char]] == char]
            print("Take out non green chars to", len(pos_answers))
            # Take out any words not containing any yellow characters
            for char in PRESENT_CHARS:
                pos_answers = [word for word in pos_answers if char in word]
            print("Take out non yellow chars to", len(pos_answers))
            # Take out words with invalid characters
            pos_answers = [word for word in pos_answers if not any(char in word for char in INVALID_CHARS)]
            print("Reduced invalid chars to", len(pos_answers))

            # Check if user want to guess if the word is easy enough to guess
            if LAST_MILE and len(pos_answers) < N_LAST_MILE:
                keep_guessing = input(f"All remaining valid guesses are:\n{pos_answers}\nDo you want to continue automated guessing?(Y/n)")
                if keep_guessing.lower() != 'y':
                    print("Good luck.")
                    exit()
                LAST_MILE = False
                gui.moveTo(guess_area_x, guess_area_y)
                gui.click()
            
            # New guess
            random_guess(pos_answers) # Need to come up with something better than random guessing

        time.sleep(1.4) # Wait for answers to animate in

        # Check which characters we got right
        guess = len(GUESSES) - 1
        i = 0
        while i < WORD_LENGTH:
            char = GUESSES[-1][i]
            x = left + offset_x * i + TOPLEFT_OFFSET
            y = top + offset_y * guess + TOPLEFT_OFFSET

            if DEBUG:
                print(f"Checking pixel ({x},{y}) with color {gui.pixel(x, y)}")
                gui.moveTo(x, y)

            color = 0
            if gui.pixelMatchesColor(x, y, GREEN, 10):
                color = 2
                CORRECT_CHARS[char] = i
                if char in PRESENT_CHARS:
                    PRESENT_CHARS.remove(char)
            if gui.pixelMatchesColor(x, y, YELLOW, 10):
                color = 1
                PRESENT_CHARS.add(char)
            if gui.pixelMatchesColor(x, y, GRAY, 10):
                color = -1
                if not (char in CORRECT_CHARS.keys() or char in PRESENT_CHARS):
                    INVALID_CHARS.add(char)
            
            i += 1
            
            if not color:
                i = 0
                input("Something is blocking the game view. Please clear any obstruction and press any key to continue: ")
                gui.moveTo(guess_area_x, guess_area_y)
                gui.click()
        
        if len(CORRECT_CHARS) == WORD_LENGTH:
            break

        print("CORRECT CHARACTERS:", CORRECT_CHARS)
        print("PRESENT CHARACTERS:", PRESENT_CHARS)
        print("INVALID CHARACTERS:", INVALID_CHARS)
        print("---------------------------------------")
    if len(CORRECT_CHARS) < WORD_LENGTH:
        print("Wordle failed... Try again tomorrow")
    else:
        print(f"Wordle completed! The word of the day is: {''.join(GUESSES[-1]).upper()}")