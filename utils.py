from typing import List, Tuple, Dict, Any, Optional

def assign_clue_numbers(grid: List[List[str]],
                        words: List[Dict[str, Any]],
                        empty: str = ' ') -> Dict[str, Any]:
    rows = len(grid)
    cols = len(grid[0]) if rows else 0

    starts = {}  # (r,c,vertical) -> word dict
    for w in words:
        r = int(w['row'])
        c = int(w['col'])
        vert = bool(w.get('vertical', False))
        starts[(r, c, vert)] = w

    number_grid: List[List[Optional[int]]] = [[None for _ in range(cols)] for _ in range(rows)]
    number = 1
    clues_all: List[Dict[str, Any]] = []

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == empty:
                continue

            starts_across = False
            starts_down = False

            if (c == 0 or grid[r][c-1] == empty) and ((r, c, False) in starts):
                starts_across = True

            if (r == 0 or grid[r-1][c] == empty) and ((r, c, True) in starts):
                starts_down = True

            if starts_across or starts_down:
                number_grid[r][c] = number

                if starts_across:
                    w = starts[(r, c, False)]
                    clues_all.append({
                        'number': number,
                        'orientation': 'across',
                        'word': w['word'],
                        'clue': w.get('clue'),
                        'row': r,
                        'col': c,
                    })
                if starts_down:
                    w = starts[(r, c, True)]
                    clues_all.append({
                        'number': number,
                        'orientation': 'down',
                        'word': w['word'],
                        'clue': w.get('clue'),
                        'row': r,
                        'col': c,
                    })

                number += 1

    across = sorted([c for c in clues_all if c['orientation'] == 'across'], key=lambda x: x['number'])
    down = sorted([c for c in clues_all if c['orientation'] == 'down'], key=lambda x: x['number'])

    return {
        'number_grid': number_grid,
        'clues': clues_all,
        'across': across,
        'down': down
    }