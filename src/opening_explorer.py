import json
import threading
import requests
from pathlib import Path

CHESSDB_URL = "https://www.chessdb.cn/cdb.php"
HEADERS     = {"User-Agent": "voice-chess/1.0"}
CACHE_FILE  = Path(__file__).parent.parent / "data" / "opening_cache.json"


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(cache: dict):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CACHE_FILE)


class OpeningExplorer:
    def __init__(self):
        self._cache: dict       = _load_cache()
        self._disk_lock         = threading.Lock()
        self._state_lock        = threading.Lock()
        self._current_fen: str  = ""
        self._moves: list       = []
        self._loading: bool     = False
        print(f"Opening-Cache geladen: {len(self._cache)} Stellungen")

    def fetch(self, fen: str):
        if fen == self._current_fen and not self._loading:
            return
        self._current_fen = fen
        if fen in self._cache:
            with self._state_lock:
                self._moves = self._cache[fen]
            return
        self._loading = True
        threading.Thread(target=self._do_fetch, args=(fen,), daemon=True).start()

    def _do_fetch(self, fen: str):
        try:
            r = requests.get(
                CHESSDB_URL,
                params={"action": "queryall", "board": fen, "json": 1},
                headers=HEADERS,
                timeout=8,
            )
            r.raise_for_status()
            data  = r.json()
            moves = self._parse_moves(data)
            self._cache[fen] = moves
            threading.Thread(
                target=self._persist, args=(dict(self._cache),), daemon=True
            ).start()
            with self._state_lock:
                if self._current_fen == fen:
                    self._moves = moves
        except Exception as e:
            with self._state_lock:
                self._moves = [{"error": str(e)}]
        finally:
            self._loading = False

    def _persist(self, snapshot: dict):
        with self._disk_lock:
            _save_cache(snapshot)

    def _parse_moves(self, data: dict) -> list:
        if data.get("status") != "ok":
            return []
        result = []
        for m in data.get("moves", [])[:6]:
            try:
                winrate = float(m.get("winrate", 50))
            except (ValueError, TypeError):
                winrate = 50.0
            score_cp = m.get("score", 0)   # centipawns, side to move
            result.append({
                "san":     m.get("san", m.get("uci", "?")),
                "winrate": winrate,          # white win% (0-100)
                "score":   score_cp,         # engine eval in cp
            })
        return result

    def get_state(self) -> tuple[list, bool]:
        """Return (moves, is_loading)."""
        with self._state_lock:
            return list(self._moves), self._loading
