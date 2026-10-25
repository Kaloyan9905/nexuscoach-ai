"""Background watcher for automatic detection of League of Legends game completion."""

import time
import threading
from typing import Callable, Optional
from nexuscoach.lcu.client import LCUClient

class LCUWatcher:
    """Monitors League client state and invokes callbacks on post-game transition."""

    def __init__(self, on_match_end: Optional[Callable[[], None]] = None, poll_interval: float = 3.0):
        self.client = LCUClient()
        self.on_match_end = on_match_end
        self.poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.last_phase: Optional[str] = None

    def start(self):
        """Start watcher thread in background."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[LCU Watcher] Started monitoring League Client state...")

    def stop(self):
        """Stop background watcher."""
        self._running = False

    def _loop(self):
        """Main polling loop."""
        while self._running:
            try:
                phase = self.client.get_gameflow_phase()
                if phase and phase != self.last_phase:
                    print(f"[LCU Gameflow] Phase changed: {self.last_phase} -> {phase}")

                    # Transition into post-game
                    if phase in ["EndOfGame", "PreEndGame", "WaitingForStats"] and self.last_phase in ["InProgress", "PreEndGame"]:
                        print("[LCU Gameflow] Game Conclusion Detected! Triggering NexusCoach AI Review...")
                        if self.on_match_end:
                            try:
                                self.on_match_end()
                            except Exception as e:
                                print(f"[LCU Error] Error in match-end callback: {e}")

                    self.last_phase = phase
            except Exception as e:
                pass

            time.sleep(self.poll_interval)

    def simulate_match_end(self):
        """Simulate an EndOfGame event for immediate verification and testing."""
        print("[LCU Simulation] Simulating EndOfGame phase transition...")
        self.last_phase = "InProgress"
        if self.on_match_end:
            self.on_match_end()
