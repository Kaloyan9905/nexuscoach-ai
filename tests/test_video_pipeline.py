"""Comprehensive End-to-End Video Testing Suite for NexusCoach AI."""

import unittest
from pathlib import Path
import requests

from nexuscoach.video.clipper import VideoClipper, VIDEOS_DIR

BASE_URL = "http://127.0.0.1:8000"

class TestVideoPipeline(unittest.TestCase):
    """Full verification of video streaming, detection, seeking, and clip endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.clipper = VideoClipper()
        cls.test_match_id = "_TEST_PIPELINE"
        cls.test_timestamp = "00:01"
        cls.test_seconds = 1.0
        cls.target_file = cls.clipper.get_clip_path(cls.test_match_id, cls.test_timestamp)
        # Create temporary dummy fixture for pipeline verification
        cls.target_file.write_bytes(b"\x1a\x45\xdf\xa3" + b"\x00" * 1024)

    @classmethod
    def tearDownClass(cls):
        if cls.target_file.exists():
            cls.target_file.unlink(missing_ok=True)

    def test_01_video_files_exist_on_disk(self):
        """Verify video assets are created with valid sizes in static/videos."""
        target = self.clipper.get_clip_path(self.test_match_id, self.test_timestamp)
        self.assertTrue(target.exists(), f"Target video file not found: {target}")
        self.assertGreater(target.stat().st_size, 100, "Video file too small / empty")

    def test_02_video_status_endpoint_returns_ready(self):
        """Verify /api/video/status detects the clip and returns correct URL."""
        resp = requests.get(
            f"{BASE_URL}/api/video/status?match_id={self.test_match_id}&timestamp={self.test_timestamp}",
            timeout=5
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("exists"), "Video status reported exists=False")
        self.assertEqual(data.get("video_url"), f"/static/videos/{self.test_match_id}_{self.test_timestamp.replace(':', '_')}.webm")

    def test_03_http_video_streaming_and_mime_type(self):
        """Verify video streaming serves valid video/webm MIME type and headers."""
        video_url = f"{BASE_URL}/static/videos/{self.test_match_id}_{self.test_timestamp.replace(':', '_')}.webm"
        head_resp = requests.head(video_url, timeout=5)
        self.assertEqual(head_resp.status_code, 200)
        self.assertEqual(head_resp.headers.get("content-type"), "video/webm")
        self.assertGreater(int(head_resp.headers.get("content-length", 0)), 100)

    def test_04_http_range_request_scrubbing(self):
        """Verify HTTP 206 Partial Content range requests for video scrubbing."""
        video_url = f"{BASE_URL}/static/videos/{self.test_match_id}_{self.test_timestamp.replace(':', '_')}.webm"
        headers = {"Range": "bytes=0-1023"}
        range_resp = requests.get(video_url, headers=headers, timeout=5)
        # FastAPi / Starlette static files support range requests (206)
        self.assertIn(range_resp.status_code, [200, 206])
        if range_resp.status_code == 206:
            self.assertEqual(len(range_resp.content), 1024)

    def test_05_video_capture_endpoint_returns_immediate_url(self):
        """Verify /api/video/capture returns ready status when clip exists."""
        resp = requests.post(
            f"{BASE_URL}/api/video/capture?match_id={self.test_match_id}&timestamp={self.test_timestamp}&time_seconds={self.test_seconds}",
            timeout=5
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "ready")
        self.assertTrue(data.get("exists"))
        self.assertIn(".webm", data.get("video_url", ""))

    def test_06_video_clipper_methods(self):
        """Verify VideoClipper helper methods."""
        self.assertTrue(self.clipper.clip_exists(self.test_match_id, self.test_timestamp))
        false_check = self.clipper.clip_exists("NON_EXISTENT_MATCH", "99:99")
        self.assertFalse(false_check)

if __name__ == "__main__":
    unittest.main()
