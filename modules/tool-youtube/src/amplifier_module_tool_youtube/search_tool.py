"""YouTube Search Tool — searches with Data API (rich filters) or yt-dlp fallback."""

import logging
from typing import Any

import yt_dlp
from amplifier_core.models import ToolResult

logger = logging.getLogger(__name__)


def build(*args: Any, **kwargs: Any) -> Any:
    """Lazy proxy — delegates to googleapiclient.discovery.build on first API call.

    Defined at module level so tests can patch amplifier_module_tool_youtube.search_tool.build
    without requiring a top-level import of google-api-python-client.
    """
    from googleapiclient.discovery import build as _build

    return _build(*args, **kwargs)


class YouTubeSearchTool:
    """Search YouTube videos. Uses Data API when api_key configured, yt-dlp otherwise."""

    _API_ONLY_ORDERS: frozenset[str] = frozenset({"viewCount", "rating"})
    _QUOTA_REASONS: frozenset[str] = frozenset(
        {
            "quotaExceeded",
            "dailyLimitExceeded",
            "rateLimitExceeded",
            "userRateLimitExceeded",
        }
    )

    def __init__(self, config: dict[str, Any]):
        self.api_key = config.get("api_key")
        self.default_max_results = config.get("max_results", 10)
        self.safe_search = config.get("safe_search", True)
        self._quota_exhausted: bool = False
        self._quota_reason: str | None = None

    @property
    def name(self) -> str:
        return "youtube-search"

    @property
    def description(self) -> str:
        return (
            "Search YouTube for videos. Routes simple keyword searches to yt-dlp (no quota cost) "
            "and rich filtered searches (duration, date range, region, HD, viewCount/rating order) "
            "to the YouTube Data API when an API key is configured. Automatically degrades to yt-dlp "
            "if the API quota is exhausted."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms"},
                "max_results": {"type": "integer", "description": "Number of results (max 50, default 10)"},
                "order": {
                    "type": "string",
                    "enum": ["relevance", "date", "viewCount", "rating"],
                    "description": "Sort order. viewCount and rating require API key; yt-dlp supports relevance and date only.",
                },
                "duration": {
                    "type": "string",
                    "enum": ["any", "short", "medium", "long"],
                    "description": "short=<4min, medium=4-20min, long=>20min. Requires API key.",
                },
                "published_after": {
                    "type": "string",
                    "description": "ISO 8601 date filter (e.g. 2025-01-01T00:00:00Z). Requires API key.",
                },
                "published_before": {"type": "string", "description": "ISO 8601 date filter. Requires API key."},
                "region_code": {
                    "type": "string",
                    "description": "ISO 3166-1 alpha-2 country code (e.g. US). Requires API key.",
                },
                "hd_only": {"type": "boolean", "description": "Filter for HD content only. Requires API key."},
                "force_backend": {
                    "type": "string",
                    "enum": ["api", "ytdlp"],
                    "description": (
                        "Force a specific backend, bypassing smart routing. "
                        "'api' requires an API key and non-exhausted quota. "
                        "'ytdlp' skips the API entirely. Omit for default smart routing."
                    ),
                },
            },
            "required": ["query"],
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _needs_api_filters(self, params: dict[str, Any]) -> list[str]:
        """Return list of API-only filter names that are present in *params*."""
        filters: list[str] = []
        if params.get("duration") and params["duration"] != "any":
            filters.append("duration")
        if params.get("published_after"):
            filters.append("published_after")
        if params.get("published_before"):
            filters.append("published_before")
        if params.get("region_code"):
            filters.append("region_code")
        if params.get("hd_only"):
            filters.append("hd_only")
        if params.get("order") in self._API_ONLY_ORDERS:
            filters.append("order")
        return filters

    @staticmethod
    def _is_quota_error(exc: Exception) -> tuple[bool, str | None]:
        """Return (True, reason) if *exc* is an HttpError 403 with a quota reason."""
        try:
            from googleapiclient.errors import HttpError
        except ImportError:
            return False, None
        if not isinstance(exc, HttpError):
            return False, None
        if exc.resp.status != 403:
            return False, None
        # Prefer structured error_details if available.
        details = getattr(exc, "error_details", None) or []
        for detail in details:
            reason = detail.get("reason", "")
            if reason in YouTubeSearchTool._QUOTA_REASONS:
                return True, reason
        # Fall back to the top-level .reason string.
        reason = getattr(exc, "reason", None) or ""
        if reason in YouTubeSearchTool._QUOTA_REASONS:
            return True, reason
        return False, None

    def _mark_quota_exhausted(self, reason: str | None) -> None:
        """Record quota exhaustion; logs once on first detection."""
        if not self._quota_exhausted:
            logger.warning(
                "YouTube Data API quota exhausted (reason=%s). Subsequent requests will use yt-dlp.",
                reason,
            )
        self._quota_exhausted = True
        self._quota_reason = reason

    # ------------------------------------------------------------------
    # Internal yt-dlp runner (centralises error handling)
    # ------------------------------------------------------------------

    async def _run_ytdlp_safe(
        self,
        params: dict[str, Any],
        max_results: int,
        backend: str = "ytdlp",
        degraded_filters: list[str] | None = None,
    ) -> ToolResult:
        """Call _search_with_ytdlp, converting exceptions to error ToolResults."""
        try:
            return await self._search_with_ytdlp(
                params, max_results, backend=backend, degraded_filters=degraded_filters
            )
        except Exception as e:
            logger.error("yt-dlp search failed: %s", e, exc_info=True)
            return ToolResult(success=False, error={"message": str(e), "type": type(e).__name__})

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        try:
            return await self._route_search(input)
        except Exception as e:
            logger.error("Unexpected error in youtube-search: %s", e, exc_info=True)
            return ToolResult(success=False, error={"message": str(e), "type": type(e).__name__})

    async def _route_search(self, input: dict[str, Any]) -> ToolResult:
        """Route search to appropriate backend. Called by execute() inside a safety net."""
        query = input.get("query")
        if not query:
            return ToolResult(success=False, error={"message": "Missing required parameter: query"})

        max_results = input.get("max_results", self.default_max_results)
        force_backend = input.get("force_backend")

        # 1. Explicit yt-dlp override — skip API entirely.
        if force_backend == "ytdlp":
            return await self._run_ytdlp_safe(input, max_results)

        # 2. Explicit API override — fail hard rather than silently fall back.
        if force_backend == "api":
            if not self.api_key:
                return ToolResult(
                    success=False,
                    error={"message": "force_backend='api' requires an API key to be configured"},
                )
            if self._quota_exhausted:
                return ToolResult(
                    success=False,
                    error={
                        "message": "force_backend='api' requested but API quota is exhausted",
                        "quota_reason": self._quota_reason,
                    },
                )
            try:
                return await self._search_with_api(input, max_results)
            except Exception as e:
                is_quota, reason = self._is_quota_error(e)
                if is_quota:
                    self._mark_quota_exhausted(reason)
                logger.warning("YouTube Data API failed (%s); no fallback (force_backend='api')", e)
                return ToolResult(success=False, error={"message": str(e), "type": type(e).__name__})

        # 3. Quota already known to be exhausted — use yt-dlp, mark filters as degraded.
        if self._quota_exhausted:
            return await self._run_ytdlp_safe(
                input,
                max_results,
                backend="ytdlp_fallback",
                degraded_filters=self._needs_api_filters(input),
            )

        # 4. No API key — yt-dlp only; warn if caller requested API-only filters.
        if not self.api_key:
            api_filters = self._needs_api_filters(input)
            if api_filters:
                logger.warning(
                    "API-only filters requested but no API key configured; filters will be ignored: %s",
                    api_filters,
                )
            return await self._run_ytdlp_safe(input, max_results, degraded_filters=api_filters)

        # 5. API key present and query uses API-only filters — use the Data API.
        api_filters = self._needs_api_filters(input)
        if api_filters:
            try:
                return await self._search_with_api(input, max_results)
            except Exception as e:
                is_quota, reason = self._is_quota_error(e)
                if is_quota:
                    self._mark_quota_exhausted(reason)
                else:
                    logger.warning("YouTube Data API failed (%s), falling back to yt-dlp", e)
                return await self._run_ytdlp_safe(
                    input,
                    max_results,
                    backend="ytdlp_fallback",
                    degraded_filters=api_filters,
                )

        # 6. Simple keyword search — yt-dlp, no quota cost.
        return await self._run_ytdlp_safe(input, max_results)

    # ------------------------------------------------------------------
    # Back-end implementations
    # ------------------------------------------------------------------

    async def _search_with_api(self, params: dict[str, Any], max_results: int) -> ToolResult:
        """Call the YouTube Data API v3. Lets HttpError propagate to execute()."""
        youtube = build("youtube", "v3", developerKey=self.api_key)

        api_params: dict[str, Any] = {
            "q": params["query"],
            "part": "snippet",
            "type": "video",
            "maxResults": min(max_results, 50),
            "safeSearch": "moderate" if self.safe_search else "none",
        }

        order = params.get("order", "relevance")
        if order in ("relevance", "date", "viewCount", "rating"):
            api_params["order"] = order
        if params.get("duration") and params["duration"] != "any":
            api_params["videoDuration"] = params["duration"]
        if params.get("published_after"):
            api_params["publishedAfter"] = params["published_after"]
        if params.get("published_before"):
            api_params["publishedBefore"] = params["published_before"]
        if params.get("region_code"):
            api_params["regionCode"] = params["region_code"]
        if params.get("hd_only"):
            api_params["videoDefinition"] = "high"

        response = youtube.search().list(**api_params).execute()

        results = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            video_id = item["id"]["videoId"]
            results.append(
                {
                    "id": video_id,
                    "title": snippet["title"],
                    "channel": snippet["channelTitle"],
                    "published_at": snippet["publishedAt"][:10],
                    "description": snippet.get("description", ""),
                    "url": f"https://youtube.com/watch?v={video_id}",
                    "duration_seconds": None,
                }
            )

        return ToolResult(
            success=True,
            output={
                "results": results,
                "backend": "api",
                "total_results": len(results),
                "degraded_filters": [],
                "quota_exhausted": self._quota_exhausted,
            },
        )

    async def _search_with_ytdlp(
        self,
        params: dict[str, Any],
        max_results: int,
        backend: str = "ytdlp",
        degraded_filters: list[str] | None = None,
    ) -> ToolResult:
        order = params.get("order", "relevance")
        # API-only sort orders are silently replaced with relevance.
        if order in self._API_ONLY_ORDERS:
            order = "relevance"
        prefix = "ytsearchdate" if order == "date" else "ytsearch"
        search_query = f"{prefix}{max_results}:{params['query']}"

        ydl_opts = {"quiet": True, "extract_flat": True, "no_warnings": True}

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(search_query, download=False)

        results = []
        for entry in info.get("entries") or []:
            vid_id = entry.get("id", "")
            results.append(
                {
                    "id": vid_id,
                    "title": entry.get("title", ""),
                    "channel": entry.get("channel", entry.get("uploader", "")),
                    "published_at": entry.get("upload_date", ""),
                    "description": entry.get("description", ""),
                    "url": entry.get("url") or f"https://youtube.com/watch?v={vid_id}",
                    "duration_seconds": entry.get("duration"),
                }
            )

        return ToolResult(
            success=True,
            output={
                "results": results,
                "backend": backend,
                "total_results": len(results),
                "degraded_filters": degraded_filters or [],
                "quota_exhausted": self._quota_exhausted,
            },
        )
