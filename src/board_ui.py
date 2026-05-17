import pygame
import chess
from pathlib import Path
from opening_explorer import OpeningExplorer

SQUARE_SIZE = 80
BOARD_PX    = SQUARE_SIZE * 8
LABEL_SIZE  = 24
PANEL_WIDTH = 240

WIN_W = LABEL_SIZE + BOARD_PX + PANEL_WIDTH
WIN_H = BOARD_PX + LABEL_SIZE

# split point between move list and opening panel (pixels from top)
SPLIT_Y = 310

LIGHT        = (240, 217, 181)
DARK         = (181, 136, 99)
LABEL_BG     = (45,  45,  45)
LABEL_FG     = (210, 210, 210)
PANEL_BG     = (30,  30,  30)
PANEL_TITLE  = (200, 180,  80)
PANEL_TEXT   = (220, 220, 220)
PANEL_DIM    = (130, 130, 130)
TURN_WHITE   = (240, 240, 240)
TURN_BLACK   = (80,  80,  80)
BAR_WHITE    = (230, 230, 230)
BAR_DRAW     = (160, 160, 160)
BAR_BLACK    = (60,  60,  60)
ACCENT       = (100, 160, 220)

ASSETS_DIR = Path(__file__).parent.parent / "assets" / "pieces"

PIECE_FILES = {
    (chess.KING,   chess.WHITE): "wK.png",
    (chess.QUEEN,  chess.WHITE): "wQ.png",
    (chess.ROOK,   chess.WHITE): "wR.png",
    (chess.BISHOP, chess.WHITE): "wB.png",
    (chess.KNIGHT, chess.WHITE): "wN.png",
    (chess.PAWN,   chess.WHITE): "wP.png",
    (chess.KING,   chess.BLACK): "bK.png",
    (chess.QUEEN,  chess.BLACK): "bQ.png",
    (chess.ROOK,   chess.BLACK): "bR.png",
    (chess.BISHOP, chess.BLACK): "bB.png",
    (chess.KNIGHT, chess.BLACK): "bN.png",
    (chess.PAWN,   chess.BLACK): "bP.png",
}


def _get_san_moves(board: chess.Board) -> list[str]:
    temp = chess.Board()
    result = []
    for move in board.move_stack:
        result.append(temp.san(move))
        temp.push(move)
    return result


class BoardUI:
    def __init__(self, board: chess.Board):
        pygame.init()
        self.board    = board
        self.explorer = OpeningExplorer()
        self.screen   = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("Voice Chess")
        self.pieces  = self._load_pieces()
        self.flipped = False
        self._font_label  = pygame.font.SysFont("helveticaneue", 13, bold=True)
        self._font_moves  = pygame.font.SysFont("couriernew",    14)
        self._font_title  = pygame.font.SysFont("helveticaneue", 14, bold=True)
        self._font_open   = pygame.font.SysFont("helveticaneue", 13)
        self._font_open_b = pygame.font.SysFont("helveticaneue", 13, bold=True)
        self.running = False

    def _load_pieces(self) -> dict:
        images = {}
        for key, filename in PIECE_FILES.items():
            path = ASSETS_DIR / filename
            img = pygame.image.load(str(path)).convert_alpha()
            images[key] = pygame.transform.smoothscale(img, (SQUARE_SIZE, SQUARE_SIZE))
        return images

    def flip(self):
        self.flipped = not self.flipped

    def run(self):
        self.running = True
        clock = pygame.time.Clock()
        # initial fetch
        self.explorer.fetch(self.board.fen())
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_f:
                        self.flip()
                    elif event.key == pygame.K_u:
                        if self.board.move_stack:
                            self.board.pop()
                            self.explorer.fetch(self.board.fen())
            self._draw()
            clock.tick(30)
        pygame.quit()

    def refresh(self):
        self.explorer.fetch(self.board.fen())
        self._draw()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _square_xy(self, file: int, rank: int) -> tuple[int, int]:
        col = (7 - file) if self.flipped else file
        row = rank       if self.flipped else (7 - rank)
        return LABEL_SIZE + col * SQUARE_SIZE, row * SQUARE_SIZE

    # ── drawing ───────────────────────────────────────────────────────────────

    def _draw(self):
        self.screen.fill(LABEL_BG)
        self._draw_squares()
        self._draw_labels()
        self._draw_pieces()
        self._draw_moves_panel()
        self._draw_opening_panel()
        pygame.display.flip()

    def _draw_squares(self):
        for rank in range(8):
            for file in range(8):
                color = DARK if (rank + file) % 2 == 0 else LIGHT
                x, y = self._square_xy(file, rank)
                pygame.draw.rect(self.screen, color, (x, y, SQUARE_SIZE, SQUARE_SIZE))

    def _draw_labels(self):
        files = "abcdefgh"
        ranks = "12345678"
        for file in range(8):
            surf = self._font_label.render(files[file], True, LABEL_FG)
            x, _ = self._square_xy(file, 0)
            x += (SQUARE_SIZE - surf.get_width()) // 2
            self.screen.blit(surf, (x, BOARD_PX + (LABEL_SIZE - surf.get_height()) // 2))
        for rank in range(8):
            surf = self._font_label.render(ranks[rank], True, LABEL_FG)
            _, y = self._square_xy(0, rank)
            y += (SQUARE_SIZE - surf.get_height()) // 2
            self.screen.blit(surf, ((LABEL_SIZE - surf.get_width()) // 2, y))

    def _draw_pieces(self):
        for rank in range(8):
            for file in range(8):
                piece = self.board.piece_at(chess.square(file, rank))
                if piece:
                    self.screen.blit(self.pieces[(piece.piece_type, piece.color)],
                                     self._square_xy(file, rank))

    # ── moves panel (top half of sidebar) ────────────────────────────────────

    def _draw_moves_panel(self):
        px = LABEL_SIZE + BOARD_PX
        pygame.draw.rect(self.screen, PANEL_BG, (px, 0, PANEL_WIDTH, SPLIT_Y))

        # turn indicator
        tc = TURN_WHITE if self.board.turn == chess.WHITE else TURN_BLACK
        tl = "White to move" if self.board.turn == chess.WHITE else "Black to move"
        pygame.draw.circle(self.screen, tc,       (px + 16, 16), 9)
        pygame.draw.circle(self.screen, LABEL_FG, (px + 16, 16), 9, 1)
        self.screen.blit(self._font_title.render(tl, True, PANEL_TITLE), (px + 30, 8))
        pygame.draw.line(self.screen, LABEL_BG, (px + 6, 30), (px + PANEL_WIDTH - 6, 30), 1)

        # move list
        san_moves = _get_san_moves(self.board)
        line_h    = 19
        y         = 36
        max_rows  = (SPLIT_Y - y) // line_h

        pairs = [(i // 2 + 1, san_moves[i], san_moves[i + 1] if i + 1 < len(san_moves) else "")
                 for i in range(0, len(san_moves), 2)]

        for num, w, b in pairs[-max_rows:]:
            self.screen.blit(self._font_moves.render(f"{num:>2}.", True, PANEL_DIM),  (px + 6,   y))
            self.screen.blit(self._font_moves.render(f"{w:<7}",    True, PANEL_TEXT), (px + 34,  y))
            self.screen.blit(self._font_moves.render(b,             True, PANEL_TEXT), (px + 120, y))
            y += line_h

    # ── opening panel (bottom half of sidebar) ───────────────────────────────

    def _draw_opening_panel(self):
        px = LABEL_SIZE + BOARD_PX
        oy = SPLIT_Y
        pygame.draw.rect(self.screen, (22, 22, 22), (px, oy, PANEL_WIDTH, WIN_H - oy))
        pygame.draw.line(self.screen, ACCENT, (px + 6, oy + 1), (px + PANEL_WIDTH - 6, oy + 1), 1)

        moves, loading = self.explorer.get_state()

        self.screen.blit(
            self._font_title.render("Opening Explorer", True, ACCENT),
            (px + 8, oy + 6),
        )

        if loading and not moves:
            self.screen.blit(self._font_open.render("Lade…", True, PANEL_DIM), (px + 8, oy + 28))
            return

        if not moves:
            self.screen.blit(self._font_open.render("Keine Daten", True, PANEL_DIM), (px + 8, oy + 28))
            return

        if moves and "error" in moves[0]:
            self.screen.blit(
                self._font_open.render(f"Fehler: {moves[0]['error'][:28]}", True, (200, 80, 80)),
                (px + 8, oy + 28),
            )
            return

        # column headers
        y = oy + 26
        self.screen.blit(self._font_open.render("Zug",     True, PANEL_DIM), (px + 8,   y))
        self.screen.blit(self._font_open.render("Gewinn%", True, PANEL_DIM), (px + 68,  y))
        self.screen.blit(self._font_open.render("Eval",    True, PANEL_DIM), (px + 168, y))
        y += 15

        bar_w = PANEL_WIDTH - 16
        row_h = 34

        for m in moves:
            if y + row_h > WIN_H - 4:
                break

            # move name
            self.screen.blit(self._font_open_b.render(m["san"], True, PANEL_TEXT), (px + 8, y))

            # win rate
            wr = m["winrate"]
            wr_color = (120, 200, 120) if wr > 52 else (200, 120, 120) if wr < 48 else PANEL_TEXT
            self.screen.blit(
                self._font_open_b.render(f"{wr:.1f}%", True, wr_color),
                (px + 68, y),
            )

            # engine eval (centipawns → pawns)
            cp = m["score"]
            eval_str = f"+{cp/100:.2f}" if cp > 0 else f"{cp/100:.2f}" if cp < 0 else "0.00"
            self.screen.blit(self._font_open.render(eval_str, True, PANEL_DIM), (px + 168, y))

            # win-rate bar
            y += 15
            fill = int(bar_w * wr / 100)
            pygame.draw.rect(self.screen, BAR_BLACK, (px + 8,        y, bar_w, 9))
            pygame.draw.rect(self.screen, BAR_WHITE, (px + 8,        y, fill,  9))
            pygame.draw.rect(self.screen, PANEL_DIM, (px + 8 + fill, y, 1,     9))  # midpoint tick

            y += 15
