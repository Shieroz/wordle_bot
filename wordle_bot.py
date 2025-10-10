import requests, os, time, random, re, string
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
MANUAL_MODE = True

WORD_LENGTH = 5
TOTAL_GUESSES = 6
GUESSES = []
ALLOW_LIST = []
for i in range(WORD_LENGTH):
    ALLOW_LIST.append(list(string.ascii_lowercase))
YELLOW_CHARS = set()

# Global vars
answer_list = []
allowed_list = []

def update_lists():
    response = requests.get(ALLOWED_LIST_URL)
    with open(ALLOWED_LIST_FILE, "w") as f:
        f.write(response.text)
        f.write('\n')

    response = requests.get(ANSWER_LIST_URL)
    with open(ANSWER_LIST_FILE, "w") as f:
        f.write(response.text)
        f.write('\n')

def load_vocab():
    with open(ALLOWED_LIST_FILE, "r") as f:
        lines = f.readlines()
        allowed_list.extend([line[:-1] for line in lines])

    with open(ANSWER_LIST_FILE, "r") as f:
        lines = f.readlines()
        answer_list.extend([line[:-1] for line in lines])

def input_guess(guess: str = "adieu"):
    guess = guess.lower()
    if not MANUAL_MODE:
        gui.write(guess, interval=0.1)
        gui.press('enter')
    print(f"GUESS {len(GUESSES)+1}: {guess.upper()}")
    GUESSES.append(guess)

def random_guess():
    global answer_list
    input_guess(answer_list[random.randint(0, len(answer_list)-1)])

def update_answer():
    global answer_list
    # Eliminate words not matching new criteria
    for i, list in enumerate(ALLOW_LIST):
        answer_list = [word for word in answer_list if word[i] in list]
    for char in YELLOW_CHARS:
        answer_list = [word for word in answer_list if char in word]
    print("Number of remaining valid words:", len(answer_list))

def input_color(color: str = "GRAY", index: int = 0, char: str = 'a'):
    if color == "GRAY" and char not in YELLOW_CHARS:
        for list in ALLOW_LIST:
            try:
                list.remove(char)
            except ValueError:
                continue
    elif color == "YELLOW":
        ALLOW_LIST[index].remove(char)
        YELLOW_CHARS.add(char)
    elif color == "GREEN":
        ALLOW_LIST[index] = [char]
        try:
            YELLOW_CHARS.remove(char)
        except KeyError:
            pass

def manual_mode():
    global answer_list
    print("Please type in current guesses and it's color. i.e. HELLO YG---. Enter nothing when you're done")
    guess = True
    while guess and len(GUESSES) < TOTAL_GUESSES:
        guess = input(f"# {len(GUESSES)+1} guess: ")
        match = re.search(r"^([a-zA-Z]{5})[ ]([yYgG-]{5})$", guess)
        if match:
            text = match.group(1).lower()
            colors = match.group(2).upper()
            input_guess(text)
            for i, color in enumerate(colors):
                char = text[i]
                if color == '-':
                    input_color("GRAY", i, char)
                elif color == 'Y':
                    input_color("YELLOW", i, char)
                elif color == 'G':
                    input_color("GREEN", i, char)
            print("Allow list:")
            for list in ALLOW_LIST:
                print(list)
            update_answer()
            print(f"Valid guesses:\n{answer_list}")
        else:
            print("Invalid format. Please enter the guess again.")
        
        if len(answer_list) == 1:
            print(f"Wordle completed! The word of the day is: {answer_list[0].upper()}")
            return

    if len(GUESSES) == TOTAL_GUESSES:
        print(f"Game over. Here are the remaining valid guesses:\n{answer_list}")

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

    if MANUAL_MODE:
        manual_mode()
        exit()

    guess_area = gui.locateOnScreen(GUESSES_PNG)
    #keyboard_area = gui.locateOnScreen(KEYBOARD_PNG)
    print("Guess area: ", guess_area)
    #print("Keyboard area: ", keyboard_area)

    # Focus on play area
    guess_area_x, guess_area_y = gui.center(guess_area)
    gui.moveTo(guess_area_x, guess_area_y)
    gui.click()

    # Block offsets
    offset_x = guess_area.width // 5
    offset_y = guess_area.height // 6
    top = guess_area.top
    left = guess_area.left

    while len(GUESSES) < TOTAL_GUESSES:
        if not GUESSES:
            # Choose a word for the initial guess, it should cover a large range of vowels to make subsequent guesses easier
            random_guess()
        else:
            update_answer()

            # Check if user want to guess if the word is easy enough to guess
            if LAST_MILE and len(answer_list) < N_LAST_MILE:
                keep_guessing = input(f"All remaining valid guesses are:\n{answer_list}\nDo you want to continue automated guessing?(Y/n)")
                if keep_guessing.lower() != 'y':
                    print("Good luck.")
                    exit()
                LAST_MILE = False
                gui.moveTo(guess_area_x, guess_area_y)
                gui.click()
            
            # New guess
            random_guess() # Need to come up with something better than random guessing

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

            color = False
            if gui.pixelMatchesColor(x, y, GRAY, 10):
                color = True
                input_color("GRAY", i, char)
            elif gui.pixelMatchesColor(x, y, YELLOW, 10):
                color = True
                input_color("YELLOW", i, char)
            elif gui.pixelMatchesColor(x, y, GREEN, 10):
                color = True
                input_color("GREEN", i, char)
            
            i += 1
            
            if not color:
                i = 0
                input("Something is blocking the game view. Please clear any obstruction and press any key to continue: ")
                gui.moveTo(guess_area_x, guess_area_y)
                gui.click()
            if len(answer_list) == 1:
                print(f"Wordle completed! The word of the day is: {answer_list[0].upper()}")
                break

        if len(GUESSES) == TOTAL_GUESSES:
            print(f"Game over. Here are the remaining valid guesses:\n{answer_list}")