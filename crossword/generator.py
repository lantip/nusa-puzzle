"""
Modified version of Crossword generator from https://github.com/sealhuang/pycrossword
"""
import random
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple, Dict, Any

# -------------------------
# Data structures
# -------------------------
@dataclass
class WordDef:
    word: str
    clue: Optional[str] = None
    row: Optional[int] = None   # start row (0-indexed)
    col: Optional[int] = None   # start col (0-indexed)
    vertical: Optional[bool] = None

    def copy_shallow(self):
        return WordDef(self.word, self.clue, self.row, self.col, self.vertical)


# -------------------------
# Crossword generator
# -------------------------
class Crossword:
    """
    Improved crossword generator based on the GitHub snippet.
    Usage:
        cw = Crossword(rows=15, cols=15, available_words=[("apple","clue"), ...])
        cw.compute_crossword(time_permitted=2.0)
        result = cw.to_json()
    """

    def __init__(self, rows: int = 15, cols: int = 15, empty: str = ' ', available_words: Optional[List[Tuple[str, str]]] = None):
        self.rows = int(rows)
        self.cols = int(cols)
        self.empty = empty
        # normalize available words into WordDef list (do not mutate caller list)
        aw = available_words or []
        self.available_words: List[WordDef] = [WordDef(w.strip().upper(), (c.strip() if c is not None else None)) for w, c in aw]
        self.let_coords: Dict[str, List[Tuple[int, int, bool]]] = defaultdict(list)
        self.grid: List[List[str]] = []
        self.current_wordlist: List[WordDef] = []
        self.best_wordlist: List[WordDef] = []
        self.best_grid: List[List[str]] = []

    # -------------------------
    # Helpers / initialization
    # -------------------------
    def _clear(self):
        self.grid = [[self.empty for _ in range(self.cols)] for _ in range(self.rows)]
        self.current_wordlist = []
        self.let_coords.clear()

    def prep_grid_words(self):
        """Prepare a fresh grid and place the first seed word."""
        self._clear()
        # work on a shallow copy of available words
        self.available_words = [wd.copy_shallow() for wd in self.available_words]
        if not self.available_words:
            return
        # seed first word (prefer vertical center)
        self.first_word(self.available_words[0])

    # -------------------------
    # Public compute API
    # -------------------------
    def compute_crossword(self, time_permitted: float = 1.0):
        """
        Attempt to build the best crossword within the time limit.
        Returns structured JSON (same as to_json).
        """
        time_permitted = float(time_permitted)
        start = time.time()
        self.best_wordlist = []
        self.best_grid = None

        # keep a deterministic order by default: longest first
        base_wordlist = sorted(self.available_words, key=lambda w: len(w.word), reverse=True)

        # If the list is long, limiting to top N helps quality and speed
        MAX_USE_WORDS = min(len(base_wordlist), 30)
        base_wordlist = base_wordlist[:MAX_USE_WORDS]

        while (time.time() - start) < time_permitted:
            # fresh grid & words copy
            self._clear()
            # deep-ish copy of words list (shallow dataclass copies)
            self.current_wordlist = []
            self.let_coords.clear()
            working = [wd.copy_shallow() for wd in base_wordlist]

            # randomize order (but keep longer words early sometimes)
            if random.random() < 0.5:
                random.shuffle(working)

            # seed and attempt to add words (two passes helps)
            if working:
                self.first_word(working[0])
                for _ in range(2):  # two passes to try different placements
                    for w in working:
                        if not any(x.word == w.word for x in self.current_wordlist):
                            self.add_words(w)

            # score candidate
            score = self._score_grid()
            best_score = self._score_grid(self.best_grid) if self.best_grid is not None else -1
            if score > best_score:
                # store copies for best solution
                self.best_grid = [row[:] for row in self.grid]
                self.best_wordlist = [wd.copy_shallow() for wd in self.current_wordlist]

            # early exit if we placed all words
            if len(self.best_wordlist) == len(base_wordlist):
                break

        # fallback if nothing placed
        if self.best_grid is None:
            self.best_grid = [row[:] for row in self.grid]
            self.best_wordlist = [wd.copy_shallow() for wd in self.current_wordlist]

        # restore best into object
        self.grid = [row[:] for row in self.best_grid]
        self.current_wordlist = [wd.copy_shallow() for wd in self.best_wordlist]

        return self.to_json()

    # -------------------------
    # Core coordinate logic
    # -------------------------
    def get_coords(self, word: WordDef) -> Optional[List[Tuple[int, int, bool, int]]]:
        """
        For a candidate WordDef (word.word), return a list of placement candidates:
        list of tuples (row, col, vertical, score), sorted descending by score.
        If none, return None.
        """
        candidates: List[Tuple[int, int, bool, int]] = []
        w = word.word
        length = len(w)
        # iterate each letter position in word, look up that letter on board
        for letter_index, ch in enumerate(w):
            coords_for_letter = self.let_coords.get(ch, [])
            if not coords_for_letter:
                continue
            for (r, c, placed_vertical) in coords_for_letter:
                # if letter in placed word was vertical, candidate is horizontal (and vice versa)
                # compute potential start cell depending on orientation
                # try horizontal placement (crossing a vertical)
                if placed_vertical:
                    start_row = r - letter_index
                    start_col = c
                    if not (0 <= start_row <= self.rows - length):
                        continue
                    if not (0 <= start_col <= self.cols - length):
                        continue
                    if 0 <= start_row <= self.rows - length:
                        score = self.check_score_horiz(w, start_row, start_col, length)
                        if score:
                            candidates.append((start_row, start_col, False, score))
                else:
                    # placed letter was horizontal -> candidate vertical placement
                    start_row = r
                    start_col = c - letter_index
                    if not (0 <= start_row <= self.rows - length):
                        continue
                    if not (0 <= start_col <= self.cols - length):
                        continue
                    if 0 <= start_col <= self.cols - length:
                        score = self.check_score_vert(w, start_row, start_col, length)
                        if score:
                            candidates.append((start_row, start_col, True, score))

        if not candidates:
            return None
        # sort by score descending and return
        candidates.sort(key=lambda tup: tup[3], reverse=True)
        return candidates

    # -------------------------
    # Seed / Add words
    # -------------------------
    def first_word(self, word: WordDef):
        """
        Place first word near center with preference for vertical orientation.
        """
        w = word.word
        length = len(w)
        # prefer vertical in center to encourage crossings
        vertical = True if random.random() < 0.75 else False
        if vertical:
            row = max(0, (self.rows - length) // 2)
            col = random.randint(0, max(0, self.cols - 1))
        else:
            col = max(0, (self.cols - length) // 2)
            row = random.randint(0, max(0, self.rows - 1))
        # bounds check
        row = min(max(0, row), self.rows - (length if vertical else 1))
        col = min(max(0, col), self.cols - (1 if vertical else length))
        self.set_word(word, row, col, vertical)

    def add_words(self, word: WordDef):
        """
        Attempt to place word by intersection candidates. Chooses among top N candidates randomly
        to avoid deterministic local maxima.
        """
        candidates = self.get_coords(word)
        if not candidates:
            return False

        # take top K candidates and randomly choose one to diversify placements
        TOP_K = min(6, len(candidates))
        top_candidates = candidates[:TOP_K]

        # bias toward placements that increase crossing density but allow some randomness
        weights = [c[3] for c in top_candidates]
        # if all weights equal, fallback to uniform
        if max(weights) == min(weights):
            choice = random.choice(top_candidates)
        else:
            # normalize weights to probabilities (plus small epsilon)
            total = sum(weights) + 1e-6
            probs = [w / total for w in weights]
            choice = random.choices(top_candidates, weights=probs, k=1)[0]

        row, col, vertical, score = choice
        # only set if valid (extra safety)
        if vertical:
            if not (0 <= row <= self.rows - len(word.word)):
                return False
        else:
            if not (0 <= col <= self.cols - len(word.word)):
                return False

        return self.set_word(word, row, col, vertical)

    # -------------------------
    # Scoring & placement checks
    # -------------------------
    def check_score_horiz(self, word_str: str, row: int, col: int, length: int, score: int = 1) -> int:
        # ensure before/after indices are in bounds when checked
        if col - 1 >= 0:
            if not (0 <= row < self.rows and 0 <= (col - 1) < self.cols):
                return 0
            if self.cell_occupied(row, col - 1):
                return 0
        if col + length < self.cols:
            if not (0 <= row < self.rows and 0 <= (col + length) < self.cols):
                return 0
            if self.cell_occupied(row, col + length):
                return 0

        for i in range(length):
            r = row
            c = col + i
            # defensive bounds check
            if not (0 <= r < self.rows and 0 <= c < self.cols):
                return 0

            active_cell = self.grid[r][c]
            ch = word_str[i]
            if active_cell == self.empty:
                # prevent touching vertically
                if (r - 1 >= 0 and 0 <= (r - 1) < self.rows and 0 <= c < self.cols and self.cell_occupied(r - 1, c)) \
                or (r + 1 < self.rows and 0 <= (r + 1) < self.rows and 0 <= c < self.cols and self.cell_occupied(r + 1, c)):
                    return 0
            elif active_cell == ch:
                score += 1
            else:
                return 0
        return score


    def check_score_vert(self, word_str: str, row: int, col: int, length: int, score: int = 1) -> int:
        # before/after checks
        if row - 1 >= 0:
            if not (0 <= (row - 1) < self.rows and 0 <= col < self.cols):
                return 0
            if self.cell_occupied(row - 1, col):
                return 0
        if row + length < self.rows:
            if not (0 <= (row + length) < self.rows and 0 <= col < self.cols):
                return 0
            if self.cell_occupied(row + length, col):
                return 0

        for i in range(length):
            r = row + i
            c = col
            # defensive bounds check
            if not (0 <= r < self.rows and 0 <= c < self.cols):
                return 0

            active_cell = self.grid[r][c]
            ch = word_str[i]
            if active_cell == self.empty:
                # prevent touching horizontally
                if (c - 1 >= 0 and 0 <= r < self.rows and 0 <= (c - 1) < self.cols and self.cell_occupied(r, c - 1)) \
                or (c + 1 < self.cols and 0 <= r < self.rows and 0 <= (c + 1) < self.cols and self.cell_occupied(r, c + 1)):
                    return 0
            elif active_cell == ch:
                score += 1
            else:
                return 0
        return score


    def cell_occupied(self, row: int, col: int) -> bool:
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return False
        return self.grid[row][col] != self.empty

    # -------------------------
    # Setting words into grid
    # -------------------------
    def set_word(self, word: WordDef, row: int, col: int, vertical: bool) -> bool:
        """
        Place the given WordDef on the grid; update let_coords and current_wordlist.
        Returns True on success.
        """
        s = word.word
        length = len(s)
        # final bounds guard
        if vertical:
            if row < 0 or row + length > self.rows:
                return False
        else:
            if col < 0 or col + length > self.cols:
                return False

        # Final validation against existing grid to avoid overwriting mismatches
        for i, ch in enumerate(s):
            r = row + i if vertical else row
            c = col if vertical else col + i
            if not (0 <= r < self.rows and 0 <= c < self.cols):
                return False 
            
        for i, ch in enumerate(s):
            r = row + i if vertical else row
            c = col if vertical else col + i
            if self.grid[r][c] != self.empty and self.grid[r][c] != ch:
                return False

        # Place letters and update let_coords
        for i, ch in enumerate(s):
            r = row + i if vertical else row
            c = col if vertical else col + i
            self.grid[r][c] = ch
            # store letter coordinate (letter -> list of (r,c,vertical_flag_of_PLACED_WORD))
            # placed word's orientation is vertical
            if (r, c, vertical) not in self.let_coords[ch]:
                self.let_coords[ch].append((r, c, vertical))

        # register word in current word list (store placement)
        placed = WordDef(word.word, word.clue, row, col, vertical)
        self.current_wordlist.append(placed)
        return True

    # -------------------------
    # Scoring & utilities
    # -------------------------
    def _score_grid(self, grid_override: Optional[List[List[str]]] = None) -> int:
        """
        Score grid by counting intersections and penalizing isolated letters.
        Higher is better.
        """
        G = grid_override if grid_override is not None else self.grid
        score = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if G[r][c] == self.empty:
                    continue
                neighbors = 0
                if r > 0 and G[r - 1][c] != self.empty:
                    neighbors += 1
                if r + 1 < self.rows and G[r + 1][c] != self.empty:
                    neighbors += 1
                if c > 0 and G[r][c - 1] != self.empty:
                    neighbors += 1
                if c + 1 < self.cols and G[r][c + 1] != self.empty:
                    neighbors += 1
                if neighbors >= 2:
                    score += 3   # intersection gives higher weight
                elif neighbors == 1:
                    score += 1   # continuation
                else:
                    score -= 1   # isolated letter (penalize)
        # minor boost for number of placed words
        score += len(self.current_wordlist) * 2
        return score

    def relax_grid(self, drop_fraction: float = 0.12):
        """
        Optionally remove a few words randomly to escape local maxima.
        Not used by default in compute_crossword, but available.
        """
        if not self.current_wordlist:
            return
        drop_count = max(1, int(len(self.current_wordlist) * drop_fraction))
        for _ in range(drop_count):
            w = random.choice(self.current_wordlist)
            self.remove_word(w)

    def remove_word(self, word_def: WordDef):
        """Remove a placed word from current grid and cleanup let_coords."""
        s = word_def.word
        if word_def not in self.current_wordlist:
            return
        
        for i, ch in enumerate(s):
            r = word_def.row + i if word_def.vertical else word_def.row
            c = word_def.col if word_def.vertical else word_def.col + i
            # clear cell only if no other crossing letter remains (simple approach: clear)
            # For simplicity, we'll clear and later rebuild let_coords from current_wordlist
            self.grid[r][c] = self.empty
        # remove from list
        self.current_wordlist = [w for w in self.current_wordlist if w.word != word_def.word or w.row != word_def.row or w.col != word_def.col]
        # rebuild let_coords from current_wordlist (cheap but correct)
        self.let_coords.clear()
        for wd in self.current_wordlist:
            s2 = wd.word
            for i, ch in enumerate(s2):
                rr = wd.row + i if wd.vertical else wd.row
                cc = wd.col if wd.vertical else wd.col + i
                if (rr, cc, wd.vertical) not in self.let_coords[ch]:
                    self.let_coords[ch].append((rr, cc, wd.vertical))

    # -------------------------
    # Output / serialization
    # -------------------------
    def to_json(self) -> Dict[str, Any]:
        """
        Return structured JSON describing the puzzle solution (suitable for DB).
        'grid' is a 2D array of single-character strings (empty -> self.empty).
        'words' is a list of dicts with word/clue/row/col/vertical.
        """
        words_out = []
        for wd in self.current_wordlist:
            words_out.append({
                "word": wd.word,
                "clue": wd.clue,
                "row": wd.row,
                "col": wd.col,
                "vertical": bool(wd.vertical)
            })
        return {
            "size": {"rows": self.rows, "cols": self.cols},
            "grid": self.grid,
            "words": words_out,
        }

    # textual debug view (optional)
    def to_text(self) -> str:
        return "\n".join("".join(ch if ch != self.empty else ' ' for ch in row) for row in self.grid)


# -------------------------
# Example usage (comment out in production)
# -------------------------
# if __name__ == "__main__":
#     words = [
#         ("kniggets","The French for knights."),
#         ("castanets","A musical instrument..."),
#         ("duck","An animal ..."),
#         # ...
#     ]
#     cw = Crossword(rows=15, cols=15, available_words=words)
#     solution = cw.compute_crossword(time_permitted=2.0)
#     import json
#     print(json.dumps(solution, indent=2))
