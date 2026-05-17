import threading
import queue
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
FRAME_SIZE = SAMPLE_RATE // 10       # 100ms frames
SPEECH_THRESHOLD = 0.02              # RMS above this = speech
SILENCE_FRAMES_NEEDED = 8            # 800ms silence ends utterance
MIN_SPEECH_FRAMES = 3                # ignore blips shorter than 300ms
MAX_SPEECH_SECONDS = 6               # hard cap on utterance length

# Schach-Vokabular als Kontext-Hint für Whisper
CHESS_PROMPT = (
    "Chess voice commands. Square notation: a1 b2 c3 d4 e5 f6 g7 h8. "
    "Moves: e2 e4, d2 d4, g1 f3, c1 g5. "
    "Commands: reset, new game, undo, take back, "
    "kingside castle, queenside castle, castle."
)


def _find_input_device() -> int:
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] >= 1:
            print(f"Mikrofon gefunden: [{i}] {dev['name']}")
            return i
    raise RuntimeError("Kein Mikrofon-Eingang gefunden.")


def _rms(frame: np.ndarray) -> float:
    return float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))


class VoiceInput:
    def __init__(self, model_size: str = "base", device: int = None, language: str = "en"):
        print("Lade Whisper-Modell...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.language = language
        self._device = device if device is not None else _find_input_device()
        self._audio_queue: queue.Queue = queue.Queue()
        self._callback = None
        self._thread = None
        self._stop_event = threading.Event()

    def start_listening(self, callback):
        self._callback = callback
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop_listening(self):
        self._stop_event.set()

    def _listen_loop(self):
        def audio_callback(indata, frames, time, status):
            self._audio_queue.put(indata.copy())

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                            dtype="float32", callback=audio_callback,
                            blocksize=FRAME_SIZE, device=self._device):
            print("Mikrofon aktiv — spreche jetzt...")
            self._vad_loop()

    def _vad_loop(self):
        """Voice Activity Detection: collect frames, detect speech/silence boundaries."""
        recording = False
        speech_frames = []
        silence_count = 0

        while not self._stop_event.is_set():
            try:
                frame = self._audio_queue.get(timeout=0.5).flatten()
            except queue.Empty:
                continue

            level = _rms(frame)
            is_speech = level > SPEECH_THRESHOLD

            if not recording:
                if is_speech:
                    recording = True
                    silence_count = 0
                    speech_frames = [frame]
            else:
                speech_frames.append(frame)
                if is_speech:
                    silence_count = 0
                else:
                    silence_count += 1

                too_long = len(speech_frames) >= MAX_SPEECH_SECONDS * 10
                long_enough_silence = silence_count >= SILENCE_FRAMES_NEEDED

                if long_enough_silence or too_long:
                    recording = False
                    if len(speech_frames) >= MIN_SPEECH_FRAMES:
                        audio = np.concatenate(speech_frames)
                        threading.Thread(
                            target=self._transcribe, args=(audio,), daemon=True
                        ).start()
                    speech_frames = []
                    silence_count = 0

    def _transcribe(self, audio: np.ndarray):
        segments, info = self.model.transcribe(
            audio,
            language=self.language,
            initial_prompt=CHESS_PROMPT,
            beam_size=5,
            condition_on_previous_text=False,
        )
        text = " ".join(s.text for s in segments).strip()
        if text:
            print(f"Erkannt [{info.language}]: {text}")
            if self._callback:
                self._callback(text)
