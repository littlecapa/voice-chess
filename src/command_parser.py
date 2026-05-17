import re
import chess
from dataclasses import dataclass
from typing import Optional

PROMOTION_MAP = {
    "queen": "q", "dame": "q",
    "rook": "r",  "turm": "r",
    "bishop": "b", "läufer": "b",
    "knight": "n", "horse": "n", "springer": "n",
}


@dataclass
class Action:
    kind: str   # reset | undo | flip | castle_k | castle_q | move
    move: Optional[chess.Move] = None


class CommandParser:
    def parse(self, text: str) -> Optional[Action]:
        t = re.sub(r"[,\.!?]", " ", text.lower())
        t = re.sub(r"\s+", " ", t).strip()

        if any(w in t for w in ["quit", "exit", "beenden", "tschüss", "bye"]):
            return Action("quit")

        if any(w in t for w in ["reset", "new game", "grundstellung", "neue partie", "restart"]):
            return Action("reset")

        if any(w in t for w in ["undo", "take back", "move back", "moves back",
                                  "zug zurück", "rückgängig", "zurück"]):
            return Action("undo")

        if any(w in t for w in ["flip", "rotate", "drehen", "umdrehen", "mirror"]):
            return Action("flip")

        if any(w in t for w in ["kingside castle", "castle kingside",
                                  "kleine rochade", "kurze rochade", "short castle"]):
            return Action("castle_k")

        if any(w in t for w in ["queenside castle", "castle queenside",
                                  "große rochade", "lange rochade", "long castle"]):
            return Action("castle_q")

        move = self._parse_move(t)
        if move:
            return Action("move", move)

        return None

    def _parse_move(self, text: str) -> Optional[chess.Move]:
        pattern = r'\b([a-h])\s*([1-8])\s*[-\s]?\s*([a-h])\s*([1-8])\b'
        m = re.search(pattern, text)
        if not m:
            return None

        uci = f"{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}"

        # check for promotion piece anywhere in the text
        promo = None
        for word, letter in PROMOTION_MAP.items():
            if word in text:
                promo = letter
                break

        if promo:
            uci += promo

        try:
            return chess.Move.from_uci(uci)
        except ValueError:
            return None
