"""Riot Games API Client for fetching Account, Match, and Timeline data."""

import time
import urllib.parse
from typing import Any, Dict, List, Optional
import requests

from nexuscoach.config import resolve_regional_route
from nexuscoach.ingestion.cache import MatchCache

class RiotAPIError(Exception):
    """Base exception for Riot API errors."""
    def __init__(self, status_code: int, message: str):
        super().__init__(f"Riot API Error ({status_code}): {message}")
        self.status_code = status_code
        self.message = message

class RiotClient:
    """Client for interacting with official Riot Games APIs."""

    def __init__(self, api_key: str, cache: Optional[MatchCache] = None):
        if not api_key:
            raise ValueError("Riot API Key is required.")
        self.api_key = api_key.strip()
        self.cache = cache or MatchCache()
        self.session = requests.Session()
        self.session.headers.update({
            "X-Riot-Token": self.api_key,
            "User-Agent": "NexusCoach-AI/1.0.0"
        })

    def _request(self, url: str, max_retries: int = 3) -> Dict[str, Any]:
        """Execute HTTP request with Rate-Limit (429) & backoff handling."""
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                resp = self.session.get(url, timeout=12)
            except requests.RequestException as e:
                if attempt >= max_retries:
                    raise RiotAPIError(0, f"Network error contacting Riot API: {str(e)}")
                time.sleep(1.5 * attempt)
                continue

            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", "3"))
                if attempt >= max_retries:
                    raise RiotAPIError(429, f"Rate limit exceeded. Try again in {retry_after}s.")
                time.sleep(retry_after + 1)
                continue
            elif resp.status_code == 403:
                raise RiotAPIError(403, "Forbidden. Your Riot API key is invalid or has expired (keys expire every 24h).")
            elif resp.status_code == 404:
                raise RiotAPIError(404, "Requested resource (Account, Summoner, or Match) was not found.")
            else:
                raise RiotAPIError(resp.status_code, resp.text)

        raise RiotAPIError(500, "Max retries exceeded while calling Riot API.")

    def get_puuid_by_riot_id(self, game_name: str, tag_line: str, regional_route: str = "europe") -> str:
        """Fetch PUUID using Account-v1 API: /riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}."""
        encoded_name = urllib.parse.quote(game_name.strip())
        encoded_tag = urllib.parse.quote(tag_line.strip())
        url = f"https://{regional_route}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
        data = self._request(url)
        puuid = data.get("puuid")
        if not puuid:
            raise RiotAPIError(404, f"Could not resolve PUUID for Riot ID: {game_name}#{tag_line}")
        return puuid

    def get_recent_match_ids(self, puuid: str, regional_route: str = "europe", count: int = 1) -> List[str]:
        """Fetch recent match IDs using Match-v5: /lol/match/v5/matches/by-puuid/{puuid}/ids."""
        url = f"https://{regional_route}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={count}"
        match_ids = self._request(url)
        if not isinstance(match_ids, list):
            raise RiotAPIError(500, "Unexpected response format for match IDs.")
        return match_ids

    def get_match_details(self, match_id: str, regional_route: str = "europe") -> Dict[str, Any]:
        """Fetch Match-v5 MatchDto with disk caching."""
        cached = self.cache.get_match(match_id)
        if cached:
            return cached

        url = f"https://{regional_route}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        data = self._request(url)
        self.cache.save_match(match_id, data)
        return data

    def get_match_timeline(self, match_id: str, regional_route: str = "europe") -> Dict[str, Any]:
        """Fetch Match-v5 MatchTimelineDto with disk caching."""
        cached = self.cache.get_timeline(match_id)
        if cached:
            return cached

        url = f"https://{regional_route}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
        data = self._request(url)
        self.cache.save_timeline(match_id, data)
        return data
