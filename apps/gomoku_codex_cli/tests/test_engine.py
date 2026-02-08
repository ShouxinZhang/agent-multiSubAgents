from __future__ import annotations

import unittest

from gomoku.engine import BLACK, WHITE, Move, apply_move, new_game_state


class EngineTest(unittest.TestCase):
    def test_black_wins_in_row(self) -> None:
        state = new_game_state(board_size=15)
        for col in range(5):
            self.assertTrue(apply_move(state, Move(BLACK, 7, col, "test"))["success"])
            if col < 4:
                self.assertTrue(apply_move(state, Move(WHITE, 8, col, "test"))["success"])

        self.assertEqual(state["winner"], BLACK)

    def test_reject_occupied_cell(self) -> None:
        state = new_game_state(board_size=15)
        ok = apply_move(state, Move(BLACK, 3, 3, "test"))
        self.assertTrue(ok["success"])

        bad = apply_move(state, Move(WHITE, 3, 3, "test"))
        self.assertFalse(bad["success"])

    def test_enforce_turn_order(self) -> None:
        state = new_game_state(board_size=15)
        bad = apply_move(state, Move(WHITE, 0, 0, "test"))
        self.assertFalse(bad["success"])


if __name__ == "__main__":
    unittest.main()
