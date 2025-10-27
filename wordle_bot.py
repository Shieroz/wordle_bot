import requests, os, time, random, re
import pyautogui as gui
import tkinter as tk
from tkinter import font
from string import ascii_lowercase
from datetime import datetime
from typing import List

# ENV
UPDATE_FREQ = 7
ALLOWED_LIST_FILE = "wordle_allowed_guesses.txt"
ANSWER_LIST_FILE = "wordle_answers.txt"
ALLOWED_LIST_URL = "https://gist.githubusercontent.com/cfreshman/cdcdf777450c5b5301e439061d29694c/raw/d7c9e02d45afd26e12a71b4564189a949c29e8a9/wordle-allowed-guesses.txt"
ANSWER_LIST_URL = "https://gist.githubusercontent.com/cfreshman/a03ef2cba789d8cf00c08f767e0fad7b/raw/c46f451920d5cf6326d550fb2d6abb1642717852/wordle-answers-alphabetical.txt"
GUESSES_PNG = "guesses.png"
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
# green/yellow  ->  (>=)  \
# gray          ->  (<=)  _>--> (==)
BOUNDS = {}
for char in ascii_lowercase:
    BOUNDS[char] = [0, WORD_LENGTH]

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
    # Validate guess
    if guess in answer_list or guess in allowed_list:
        gui.write(guess, interval=0.1)
        gui.press('enter')

def random_guess():
    global answer_list
    input_guess(random.choice(answer_list))

def update_answer(guess: str = "adieu", colors: List[int] = [0, 0, 0, 0, 0]) -> bool:
    """
    Update the answer list with the new guess and it's characters' color.
    Args:
        guess (str): The guess, must be of WORD_LENGTH. Can mix upper and lower cases.
        colors (List[int]): List of colors for each character in the guess, with 0-GRAY, 1-YELLOW, 2-GREEN.
    Returns:
        True if guess is valid (is an allowed guess or an answer), False otherwise
    """
    global answer_list
    guess = guess.lower()
    # Check if this is a valid guess
    if guess not in answer_list and guess not in allowed_list:
        return False

    guess = list(guess)
    GUESSES.append(guess)

    # Since the bounds method still allows words with yellow characters at the same place
    # This will eliminate all those occurrences
    for i, char in enumerate(guess):
        if colors[i] == 1:
            answer_list = [word for word in answer_list if word[i] != char]

    combined = zip(guess, colors)
    combined = sorted(combined)
    guess_sorted, colors_sorted = zip(*combined)
    chars_map = {}
    curr_group = [colors_sorted[0]]
    for i in range(1, len(guess_sorted)):
        if guess_sorted[i] == guess_sorted[i-1]:
            curr_group.append(colors_sorted[i])
        else:
            chars_map[guess_sorted[i-1]] = sorted(curr_group, reverse=True)
            curr_group = [colors_sorted[i]]
    chars_map[guess_sorted[-1]] = sorted(curr_group, reverse=True)
    if DEBUG:
        print(chars_map)

    # First, remove any words with characters not matching green characters in the guess.
    for i, color in enumerate(colors):
        if color == 2:
            answer_list = [word for word in answer_list if word[i] == guess[i]]

    # Then, we establish the bounds of each character in the guess.
    for char in chars_map.keys():
        col_map = chars_map[char]
        # The number of yellow/green determine the lower bound of a character in the answer.
        # If there are gray(s), those set the upper bound equal to the lower bound,
        # effectively tells us how many of a character is in the answer.
        try:
            # Since the list is reverse sorted, the first index of 0 in the list is both bounds.
            zero_i = col_map.index(0)
            # If this char only appears once in guess and is gray, we are sure it's not part
            # of the answer. Eliminate all words with this character
            if zero_i == 0:
                if char in BOUNDS:
                    BOUNDS.pop(char)
                answer_list = [word for word in answer_list if char not in word]
            else:
                BOUNDS[char] = [zero_i, zero_i]
        except ValueError:
            # If there are no 0, set the lower bound to the number of duplicates in the guess, or
            # a higher number from a previous guess
            BOUNDS[char][0] = max(BOUNDS[char][0], len(col_map))
        # Since we have (maybe) established a new lower bound for this character, we know that
        # other characters can't have an upper bound higher than WORD_LENGTH - lower bound. Thus,
        # we can update the upper bounds of all other characters.
        if char in BOUNDS:
            new_upper = WORD_LENGTH - BOUNDS[char][0]
            for c in BOUNDS.keys():
                if char != c:
                    BOUNDS[c][1] = min(BOUNDS[c][1], new_upper)
    if DEBUG:
        print(BOUNDS)

    # Remove all words that don't match our new bounds.
    for char in BOUNDS.keys():
        answer_list = [word for word in answer_list if BOUNDS[char][0] <= word.count(char) <= BOUNDS[char][1]]
    
    if DEBUG:
        print(answer_list)
    return True

# TODO update auto solver logic and integrate into UI
def auto_solver():
    # Get the play area
    try:
        guess_area = gui.locateOnScreen(GUESSES_PNG)
    except Exception:
        pass

    # Focus on play area
    guess_area_x, guess_area_y = gui.center(guess_area)
    gui.moveTo(guess_area_x, guess_area_y)
    gui.click()

    # Block offsets
    offset_x = guess_area.width // WORD_LENGTH
    offset_y = guess_area.height // TOTAL_GUESSES
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
        colors = []
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
                colors.append(0)
            elif gui.pixelMatchesColor(x, y, YELLOW, 10):
                color = True
                colors.append(1)
            elif gui.pixelMatchesColor(x, y, GREEN, 10):
                color = True
                colors.append(2)

            i += 1

            if not color:
                i = 0
                input("Something is blocking the game view. Please clear any obstruction and press any key to continue: ")
                gui.moveTo(guess_area_x, guess_area_y)
                gui.click()

class WordleSolverGUI:
    """
    A tkinter-based GUI for a Wordle solver application.

    This class provides the user interface for entering 5-letter guesses and
    the corresponding color feedback (gray, yellow, green) from a Wordle game.
    It features a 6x5 grid, a toggleable virtual keyboard, and a
    resizable, clickable list to display potential answers that reflows with
    window size.
    """
    # --- Constants ---
    COLORS = {
        "gray": "#787c7e",
        "yellow": "#c9b458",
        "green": "#6aaa64",
        "outline": "#3a3a3c",
        "default": "#121213",
        "white": "#ffffff"
    }
    COLORS_2_INT = {
        "#787c7e": 0,
        "#c9b458": 1,
        "#6aaa64": 2
    }
    KEYBOARD_LAYOUT = [
        "QWERTYUIOP",
        "ASDFGHJKL",
        "ZXCVBNM"
    ]
    # --- Define heights ---
    HEIGHT_KEYBOARD_HIDDEN = 400
    HEIGHT_KEYBOARD_SHOWN = 530

    def __init__(self, root):
        self.root = root
        self.root.title("Wordle Solver")
        self.root.config(bg=self.COLORS["default"])
        # Allow window resizing to accommodate the paned window
        self.root.resizable(False, False)
        self.root.geometry(f"570x{self.HEIGHT_KEYBOARD_HIDDEN}") # Set size for keyboard-hidden state

        # --- State Variables ---
        self.current_row = 0
        self.current_col = 0
        self.guesses = [["" for _ in range(WORD_LENGTH)] for _ in range(TOTAL_GUESSES)]
        self.cell_colors = [[self.COLORS["default"] for _ in range(WORD_LENGTH)] for _ in range(TOTAL_GUESSES)]
        self.manual_color_set = [[False for _ in range(WORD_LENGTH)] for _ in range(TOTAL_GUESSES)]
        self.keyboard_visible = False

        # --- Fonts ---
        self.cell_font = font.Font(family="Courier New", size=24, weight="bold")
        self.key_font = font.Font(family="Courier New", size=12)
        self.list_font = font.Font(family="Courier New", size=12)
        self.title_font = font.Font(family="Helvetica", size=20, weight="bold")
        self.final_word_font = font.Font(family="Courier New", size=48, weight="bold")

        # --- UI Frames ---
        
        # Main resizable pane
        self.main_paned_window = tk.PanedWindow(
            root, orient=tk.HORIZONTAL, 
            bg=self.COLORS["default"], sashrelief=tk.RAISED, sashwidth=4
        )
        self.main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left frame for grid and controls
        self.left_frame = tk.Frame(self.main_paned_window, bg=self.COLORS["default"])
        self.main_paned_window.add(self.left_frame, minsize=350) # Min size for grid

        # main_frame now goes inside left_frame
        self.main_frame = tk.Frame(self.left_frame, bg=self.COLORS["default"])
        self.main_frame.pack(pady=(0, 10)) # No padx, handled by paned window

        self.grid_frame = tk.Frame(self.main_frame, bg=self.COLORS["default"])
        self.grid_frame.pack(pady=(0, 10))

        self.controls_frame = tk.Frame(self.main_frame, bg=self.COLORS["default"])
        self.controls_frame.pack(pady=5)
        
        # keyboard_frame now goes inside left_frame
        self.keyboard_frame = tk.Frame(self.left_frame, bg=self.COLORS["default"], pady=10)

        # --- Initialize UI ---
        self._create_grid()
        self._create_controls()
        self._create_keyboard()
        self._create_answer_list()
        self._create_congrats_screen()
        self._create_fail_screen()
        self._create_autosolve_screen()
        self._bind_events()
        self._update_row_highlight()

    def _create_grid(self):
        """Creates the 6x5 grid of labels for guesses."""
        self.cells = []
        for i in range(TOTAL_GUESSES):
            row_cells = []
            for j in range(WORD_LENGTH):
                cell = tk.Label(
                    self.grid_frame, text="", width=2, height=1,
                    font=self.cell_font, bg=self.COLORS["default"], fg=self.COLORS["white"],
                    highlightbackground=self.COLORS["outline"], highlightthickness=2
                )
                cell.grid(row=i, column=j, padx=3, pady=3)
                cell.bind("<Button-1>", lambda e, r=i, c=j: self._handle_cell_click(r, c))
                row_cells.append(cell)
            self.cells.append(row_cells)

    def _create_controls(self):
        """Creates the control buttons (Submit and Toggle Keyboard)."""
        self.submit_button = tk.Button(
            self.controls_frame, text="➔", command=self._submit_guess,
            font=self.key_font, bg=self.COLORS["gray"], fg=self.COLORS["white"], width=5
        )
        self.submit_button.pack(side=tk.LEFT, padx=5)

        self.keyboard_toggle_button = tk.Button(
            self.controls_frame, text="Show Keyboard", command=self._toggle_keyboard,
            font=self.key_font, bg=self.COLORS["gray"], fg=self.COLORS["white"]
        )
        self.keyboard_toggle_button.pack(side=tk.LEFT, padx=5)

        self.autosolve_button = tk.Button(
            self.controls_frame, text="Auto-Solve", command=self._show_autosolve_screen,
            font=self.key_font, bg=self.COLORS["gray"], fg=self.COLORS["white"]
        )
        self.autosolve_button.pack(side=tk.LEFT, padx=5)

    def _create_keyboard(self):
        """Creates the virtual keyboard buttons."""
        for i, row_layout in enumerate(self.KEYBOARD_LAYOUT): # Use enumerate
            row_frame = tk.Frame(self.keyboard_frame, bg=self.COLORS["default"])
            row_frame.pack()
            for char in row_layout:
                key_button = tk.Button(
                    row_frame, text=char, width=2, height=1,
                    font=self.key_font, bg=self.COLORS["gray"], fg=self.COLORS["white"],
                    command=lambda c=char: self._handle_key_press(tk.Event(), key=c)
                )
                key_button.pack(side=tk.LEFT, padx=2, pady=2)
            
            # Add Backspace key to the last row
            if i == len(self.KEYBOARD_LAYOUT) - 1:
                bs_button = tk.Button(
                    row_frame, text="⌫", width=4, height=1,
                    font=self.key_font, bg=self.COLORS["gray"], fg=self.COLORS["white"],
                    command=lambda: self._handle_key_press(tk.Event(), key="BACKSPACE")
                )
                bs_button.pack(side=tk.LEFT, padx=2, pady=2)

    def _create_answer_list(self):
        """Creates the resizable, scrollable list for potential answers."""
        # Right frame for the answer list
        self.right_frame = tk.Frame(self.main_paned_window, bg=self.COLORS["default"])
        # Set minsize wide enough for ~3 words
        self.main_paned_window.add(self.right_frame, minsize=200) 

        # Label for the list
        self.list_label = tk.Label(
            self.right_frame, text="Potential Answers",
            font=self.key_font, bg=self.COLORS["default"], fg=self.COLORS["white"]
        )
        self.list_label.pack(pady=(0, 5))

        # Container for listbox and scrollbar
        self.list_container = tk.Frame(self.right_frame, bg=self.COLORS["default"])
        self.list_container.pack(fill=tk.BOTH, expand=True)

        # Scrollbar
        self.scrollbar = tk.Scrollbar(self.list_container, orient=tk.VERTICAL)
        
        # Text widget instead of Listbox for word wrapping
        self.answer_text = tk.Text(
            self.list_container,
            yscrollcommand=self.scrollbar.set,
            bg=self.COLORS["outline"],
            fg=self.COLORS["white"],
            font=self.list_font,
            highlightthickness=0,
            borderwidth=0,
            wrap="word", # This is the key change for reflowing
            state="disabled" # Start as read-only
        )
        
        self.scrollbar.config(command=self.answer_text.yview)

        # Pack scrollbar and listbox
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.answer_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Bind click event to populate guess ---
        self.answer_text.bind("<Button-1>", self._handle_answer_click)

    def _create_congrats_screen(self):
        """Creates the (hidden) congratulations frame and labels."""
        self.congrats_frame = tk.Frame(self.root, bg=self.COLORS["default"])
        
        self.congrats_label = tk.Label(
            self.congrats_frame,
            text="The word of the day is",
            font=self.title_font,
            bg=self.COLORS["default"],
            fg=self.COLORS["white"]
        )
        self.congrats_label.pack(pady=(50, 20))
        
        self.final_word_label = tk.Label(
            self.congrats_frame,
            text="", # Will be set later
            font=self.final_word_font,
            bg=self.COLORS["default"],
            fg=self.COLORS["green"] # Use green for the final word
        )
        self.final_word_label.pack(pady=20)

    def _create_fail_screen(self):
        """Creates the (hidden) failure frame and labels."""
        self.fail_frame = tk.Frame(self.root, bg=self.COLORS["default"])
        
        self.fail_label = tk.Label(
            self.fail_frame,
            text="Better luck next time!",
            font=self.title_font,
            bg=self.COLORS["default"],
            fg=self.COLORS["gray"] # Use gray for fail
        )
        self.fail_label.pack(pady=50)

    def _create_autosolve_screen(self):
        """Creates the (hidden) auto-solve placeholder screen."""
        self.autosolve_frame = tk.Frame(self.root, bg=self.COLORS["default"])
        
        self.autosolve_label = tk.Label(
            self.autosolve_frame,
            text="Auto-Solver Running...",
            font=self.title_font,
            bg=self.COLORS["default"],
            fg=self.COLORS["white"]
        )
        self.autosolve_label.pack(pady=50)
        
    def _show_congrats_screen(self, final_word):
        """Destroys the main UI and shows the congratulations screen."""
        self.main_paned_window.destroy()
        self.final_word_label.config(text=final_word.upper())
        self.congrats_frame.pack(fill=tk.BOTH, expand=True)
        self.root.resizable(False, False)
        self.root.geometry("500x300")

    def _show_fail_screen(self):
        """Destroys the main UI and shows the failure screen."""
        self.main_paned_window.destroy()
        self.fail_frame.pack(fill=tk.BOTH, expand=True)
        self.root.resizable(False, False)
        self.root.geometry("500x300")

    def _show_autosolve_screen(self):
        """Destroys the main UI and shows the auto-solve placeholder screen."""
        self.main_paned_window.destroy()
        self.autosolve_frame.pack(fill=tk.BOTH, expand=True)
        self.root.resizable(False, False)
        self.root.geometry("500x300")

    def _bind_events(self):
        """Binds keyboard events to the root window."""
        self.root.bind("<Key>", self._handle_key_press)
        
    def _set_cell(self, char):
        """Sets the current cell with a character and advances the cursor."""
        if self.current_col < WORD_LENGTH and self.current_row < TOTAL_GUESSES:
            char_upper = char.upper()
            
            # If color was not manually set, update it upon typing
            if not self.manual_color_set[self.current_row][self.current_col]:
                self.cells[self.current_row][self.current_col].config(bg=self.COLORS["gray"])
                self.cell_colors[self.current_row][self.current_col] = self.COLORS["gray"]

            self.guesses[self.current_row][self.current_col] = char_upper
            self.cells[self.current_row][self.current_col].config(text=char_upper)
            self.current_col += 1

    def _fill_current_row(self, word):
        """Helper function to fill the current guess row with a word."""
        if self.current_row >= TOTAL_GUESSES or len(word) != WORD_LENGTH:
            return
        
        # Reset col to 0 before filling
        self.current_col = 0
        
        for char in word.upper():
            # Use the set_cell logic but manage self.current_col manually
            char_upper = char.upper()
            j = self.current_col # Use self.current_col as the index
            
            self.guesses[self.current_row][j] = char_upper
            self.cells[self.current_row][j].config(text=char_upper)
            
            if not self.manual_color_set[self.current_row][j]:
                self.cells[self.current_row][j].config(bg=self.COLORS["gray"])
                self.cell_colors[self.current_row][j] = self.COLORS["gray"]
            
            self.current_col += 1 # Advance cursor
            
    def _handle_answer_click(self, event):
        """Fills the current row with the word clicked in the answer list."""
        # The Text widget must be 'normal' to get word boundaries
        self.answer_text.config(state="normal")
        
        try:
            # Get the index of the click
            click_index = self.answer_text.index("@%d,%d" % (event.x, event.y))
            
            # Get the word boundaries around that index
            word_start = self.answer_text.index(f"{click_index} wordstart")
            word_end = self.answer_text.index(f"{click_index} wordend")
            
            # Get the word
            clicked_word = self.answer_text.get(word_start, word_end).strip().upper()
        
        finally:
            # Always set state back to disabled
            self.answer_text.config(state="disabled")
        
        # Run validation
        if (len(clicked_word) != WORD_LENGTH or 
            not clicked_word.isalpha() or 
            self.current_row >= TOTAL_GUESSES):
            return
            
        # If valid, populate the grid
        self._fill_current_row(clicked_word)

    def _handle_key_press(self, event, key=None):
        """Handles physical and virtual keyboard presses."""
        if self.current_row >= TOTAL_GUESSES:
            return

        key_char = key if key else event.keysym.upper()

        if key_char == "BACKSPACE":
            if self.current_col > 0:
                self.current_col -= 1
                cell = self.cells[self.current_row][self.current_col]
                self.guesses[self.current_row][self.current_col] = ""
                
                # Clear text and reset color/manual flag
                cell.config(text="", bg=self.COLORS["default"])
                self.cell_colors[self.current_row][self.current_col] = self.COLORS["default"]
                self.manual_color_set[self.current_row][self.current_col] = False

        elif key_char == "RETURN" or key_char == "ENTER":
            self._submit_guess()

        elif len(key_char) == 1 and key_char.isalpha():
            self._set_cell(key_char) # Use the refactored method
    
    def _handle_cell_click(self, row, col):
        """Cycles through colors, but only for the current guess row."""
        # Only allow clicking on the current, active row
        if row != self.current_row:
            return

        # Do not allow color changes for empty cells
        if self.guesses[row][col] == "":
            return

        current_color = self.cell_colors[row][col]
        color_cycle = [self.COLORS["gray"], self.COLORS["yellow"], self.COLORS["green"]]
        
        try:
            current_index = color_cycle.index(current_color)
            next_index = (current_index + 1) % len(color_cycle)
        except ValueError:
            next_index = 0 # Default to gray

        new_color = color_cycle[next_index]
        self.cell_colors[row][col] = new_color
        self.cells[row][col].config(bg=new_color)
        
        # Mark that this cell's color was set manually
        self.manual_color_set[row][col] = True
        
    def _submit_guess(self):
        """Submits the current guess and moves to the next row."""
        if self.current_col == WORD_LENGTH and self.current_row < TOTAL_GUESSES:
            
            current_guess = "".join(self.guesses[self.current_row])
            current_colors = [self.COLORS_2_INT[c] for c in self.cell_colors[self.current_row]]
            # If guess is not valid, try again
            if not update_answer(current_guess, current_colors):
                return

            # Check if this is the last row *before* incrementing
            is_last_guess = (self.current_row == TOTAL_GUESSES - 1)
            
            # Call update_answer_list with the new flag
            self.update_answer_list(is_last_guess)
            
            # Don't advance the row if the game has ended
            if self.congrats_frame.winfo_ismapped() or self.fail_frame.winfo_ismapped():
                return

            self.current_row += 1
            self.current_col = 0
            if self.current_row < TOTAL_GUESSES:
                self._update_row_highlight()

    def _update_row_highlight(self):
        """Updates the highlight outline for the current active row."""
        for i in range(TOTAL_GUESSES):
            thickness = 4 if i == self.current_row else 2
            for j in range(WORD_LENGTH):
                self.cells[i][j].config(highlightthickness=thickness)

    def _toggle_keyboard(self):
        """Shows or hides the virtual keyboard and resizes window height."""
        # Get the current width to preserve it
        current_width = self.root.winfo_width()
        
        if self.keyboard_visible:
            self.keyboard_frame.pack_forget()
            self.keyboard_toggle_button.config(text="Show Keyboard")
            # Set geometry to hidden height, preserving width
            self.root.geometry(f"{current_width}x{self.HEIGHT_KEYBOARD_HIDDEN}")
        else:
            self.keyboard_frame.pack(fill="x")
            self.keyboard_toggle_button.config(text="Hide Keyboard")
            # Set geometry to shown height, preserving width
            self.root.geometry(f"{current_width}x{self.HEIGHT_KEYBOARD_SHOWN}")
        
        self.keyboard_visible = not self.keyboard_visible
        
    def update_answer_list(self, is_last_guess=False):
        """
        Public method to clear and populate the answer text widget.
        
        Args:
            answers (list): A list of strings (potential words) to display.
            is_last_guess (bool): True if this is the result of the final guess.
        """
        # --- CHECK FOR GAME END CONDITIONS ---
        if len(answer_list) == 1:
            self._show_congrats_screen(answer_list[0])
            return # Stop execution
        
        if len(answer_list) == 0 or is_last_guess: 
            # If it was the last guess and we have != 1 answers, it's a fail
            self._show_fail_screen()
            return # Stop execution
        # -----------------------------------

        # Enable the widget to modify it
        self.answer_text.config(state="normal")
        
        # Clear all previous content
        self.answer_text.delete("1.0", tk.END)
        
        # Join all words with a space to allow wrapping
        all_words = " ".join(answer.upper() for answer in answer_list)
        self.answer_text.insert("1.0", all_words)
        
        # Disable the widget to make it read-only again
        self.answer_text.config(state="disabled")

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

    root = tk.Tk()
    app = WordleSolverGUI(root)
    app.update_answer_list()
    root.mainloop()
