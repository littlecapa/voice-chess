import chess
from board_ui import BoardUI
from voice_input import VoiceInput
from command_parser import CommandParser


class Game:
    def __init__(self):
        self.board = chess.Board()
        self.ui = BoardUI(self.board)
        self.voice = VoiceInput()
        self.parser = CommandParser()

    def run(self):
        self.voice.start_listening(callback=self._on_command)
        self.ui.run()
        self.voice.stop_listening()

    def _on_command(self, text: str):
        action = self.parser.parse(text)
        if not action:
            print(f"Nicht erkannt: {text}")
            return

        if action.kind == "quit":
            self.ui.running = False

        elif action.kind == "reset":
            self.board.reset()

        elif action.kind == "undo":
            if self.board.move_stack:
                self.board.pop()
            else:
                print("Keine Züge vorhanden.")

        elif action.kind == "flip":
            self.ui.flip()

        elif action.kind == "castle_k":
            move = chess.Move.from_uci("e1g1" if self.board.turn == chess.WHITE else "e8g8")
            self._push_if_legal(move)

        elif action.kind == "castle_q":
            move = chess.Move.from_uci("e1c1" if self.board.turn == chess.WHITE else "e8c8")
            self._push_if_legal(move)

        elif action.kind == "move":
            move = action.move
            # auto-promote to queen if no promotion piece was specified
            if (not move.promotion
                    and self.board.piece_type_at(move.from_square) == chess.PAWN
                    and chess.square_rank(move.to_square) in (0, 7)):
                move = chess.Move(move.from_square, move.to_square, chess.QUEEN)
            self._push_if_legal(move)

        self.ui.refresh()

    def _push_if_legal(self, move: chess.Move):
        if move in self.board.legal_moves:
            self.board.push(move)
        else:
            print(f"Ungültiger Zug: {move.uci()}")
