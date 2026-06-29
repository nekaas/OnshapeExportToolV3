"""Onshape API client wrapper.

This module preserves the proof-of-concept's working behavior for:

- HTTP Basic authentication
- transient network retries with exponential backoff
- document paging
- label filtering through ``documentLabels``
- modified-date filtering
- default workspace and element discovery
"""

from __future__ import annotations

import time
import types
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

try:
    import requests
    from requests.auth import HTTPBasicAuth
except ModuleNotFoundError:  # pragma: no cover - real HTTP still requires requirements.txt
    class HTTPBasicAuth:  # type: ignore[no-redef]
        """Fallback auth object for fake-session unit tests."""

        def __init__(self, username: str, password: str) -> None:
            self.username = username
            self.password = password

    class _MissingRequestsSession:
        def __init__(self) -> None:
            raise RuntimeError("requests is not installed. Run `pip install -r requirements.txt`.")

    class _ConnectionError(Exception):
        pass

    class _Timeout(Exception):
        pass

    requests = types.SimpleNamespace(  # type: ignore[assignment]
        Session=_MissingRequestsSession,
        Response=Any,
        exceptions=types.SimpleNamespace(
            ConnectionError=_ConnectionError,
            Timeout=_Timeout,
        ),
    )

from onshape_export_manager.core.api_pool import ApiPool
from onshape_export_manager.core.models import ExportFormat, OnshapeAccount
from onshape_export_manager.core.retry import RetryPolicy


JSON_HEADERS = {
    "Accept": "application/vnd.onshape.v2+json",
    "Content-Type": "application/json",
}
OCTET_STREAM_HEADERS = {"Accept": "application/octet-stream"}
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
MIN_STL_BYTES = 84


class OnshapeClientError(RuntimeError):
    """Base error for Onshape client failures."""


class OnshapeApiError(OnshapeClientError):
    """Raised when Onshape returns an API error or unexpected payload."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class RequestRetryPolicy(RetryPolicy):
    """Retry settings for Onshape HTTP requests."""

    request_timeout_seconds: int = 30
    export_timeout_seconds: int = 120
    translation_timeout_seconds: int = 300
    translation_poll_interval_seconds: float = 2.0


@dataclass(frozen=True, slots=True)
class OnshapeDocument:
    """Convenience wrapper around a document payload."""

    id: str
    name: str
    modified_at: datetime | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class OnshapeElement:
    """Convenience wrapper around an element payload."""

    id: str
    name: str
    element_type: str
    raw: dict[str, Any]


@dataclass(slots=True)
class OnshapeClient:
    """Authenticated Onshape API client for one account."""

    account: OnshapeAccount
    base_url: str = "https://cad.onshape.com/api/v6"
    session: requests.Session | None = None
    retry_policy: RequestRetryPolicy = RequestRetryPolicy()
    api_pool: ApiPool | None = None
    sleep_fn: Callable[[float], None] = time.sleep

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()
        self.base_url = self.base_url.rstrip("/")

    @property
    def auth(self) -> HTTPBasicAuth:
        """Return requests-compatible authentication for this account."""
        return HTTPBasicAuth(self.account.access_key, self.account.secret_key)

    def api_get(self, url: str, *, retries: int | None = None, **kwargs: Any) -> requests.Response:
        """Run ``GET`` with authentication, timeout, and transient retries.

        This is the class-based version of the proof-of-concept ``api_get``.
        """
        return self._api_request("get", url, retries=retries, **kwargs)

    def api_post(self, url: str, *, retries: int | None = None, **kwargs: Any) -> requests.Response:
        """Run ``POST`` with authentication, timeout, and transient retries."""
        return self._api_request("post", url, retries=retries, **kwargs)

    def _api_request(
        self,
        method: str,
        url: str,
        *,
        retries: int | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Run an HTTP request with authentication, timeout, and retries."""
        assert self.session is not None
        max_attempts = retries if retries is not None else self.retry_policy.max_attempts
        if max_attempts < 1:
            raise ValueError("retries/max_attempts must be at least 1")

        full_url = self._normalize_url(url)
        kwargs.setdefault("auth", self.auth)
        kwargs.setdefault("timeout", self.retry_policy.request_timeout_seconds)
        request_fn = getattr(self.session, method)

        last_error: BaseException | None = None
        for attempt in range(max_attempts):
            try:
                response = request_fn(full_url, **kwargs)
                self._record_response(response)
                if not self._should_retry_response(response, attempt, max_attempts):
                    return response
                self._sleep_before_retry(response, attempt)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                last_error = exc
                self._record_exception(exc)
                if attempt == max_attempts - 1:
                    raise
                self.sleep_fn(self.retry_policy.delay_for_attempt(attempt))

        if last_error is not None:
            raise last_error
        raise OnshapeClientError(f"{method.upper()} request failed without a response.")

    def fetch_document(self, doc_id: str) -> dict[str, Any]:
        """Fetch one document payload."""
        response = self.api_get(f"/documents/{doc_id}", headers=JSON_HEADERS)
        self._raise_for_status(response, f"fetch document {doc_id}")
        payload = self._require_json_object(response, f"document {doc_id}")
        return payload

    def fetch_documents_by_label(
        self,
        label_id: str,
        start_iso: str,
        end_iso: str,
    ) -> list[dict[str, Any]]:
        """Fetch documents that carry a label and were modified in a date range.

        The proof-of-concept discovered that Onshape's ``/documents?label=``
        query parameter can be ignored, so this method intentionally pages
        through visible documents and filters ``documentLabels`` locally.
        """
        start_dt = parse_onshape_datetime(start_iso)
        end_dt = parse_onshape_datetime(end_iso)
        if start_dt is None or end_dt is None:
            raise ValueError("start_iso and end_iso must be valid ISO datetimes")
        if start_dt > end_dt:
            raise ValueError("start_iso must be before or equal to end_iso")

        label_docs: list[dict[str, Any]] = []
        url: str | None = "/documents?limit=20"
        while url:
            response = self.api_get(url, headers=JSON_HEADERS)
            self._raise_for_status(response, "fetch documents")
            data = self._require_json_object(response, "documents page")

            items = data.get("items", [])
            if not isinstance(items, list):
                raise OnshapeApiError("Documents response field 'items' must be a list.")

            for item in items:
                if isinstance(item, dict) and doc_has_label(item, label_id):
                    label_docs.append(item)

            next_url = data.get("next")
            if next_url is not None and not isinstance(next_url, str):
                raise OnshapeApiError("Documents response field 'next' must be a string or null.")
            url = next_url

        return [
            doc
            for doc in label_docs
            if document_matches_date_range(doc, start_dt, end_dt)
        ]

    def fetch_documents_by_label_typed(
        self,
        label_id: str,
        start_iso: str,
        end_iso: str,
    ) -> list[OnshapeDocument]:
        """Fetch labeled documents as typed wrappers."""
        return [
            document_from_payload(payload)
            for payload in self.fetch_documents_by_label(label_id, start_iso, end_iso)
        ]

    def get_default_workspace_id(self, document: dict[str, Any]) -> str:
        """Return a document's default workspace id, fetching details if needed."""
        workspace = document.get("defaultWorkspace")
        if isinstance(workspace, dict) and workspace.get("id"):
            return str(workspace["id"])

        doc_id = str(document["id"])
        full_document = self.fetch_document(doc_id)
        workspace = full_document.get("defaultWorkspace")
        if not isinstance(workspace, dict) or not workspace.get("id"):
            raise OnshapeApiError(f"Document {doc_id} does not include a default workspace.")
        return str(workspace["id"])

    def list_elements(self, doc_id: str, workspace_id: str) -> list[dict[str, Any]]:
        """List document elements for a workspace."""
        response = self.api_get(
            f"/documents/d/{doc_id}/w/{workspace_id}/elements",
            headers=JSON_HEADERS,
        )
        self._raise_for_status(response, f"list elements for document {doc_id}")
        payload = response.json()
        if not isinstance(payload, list):
            raise OnshapeApiError("Elements response must be a JSON list.")
        return [item for item in payload if isinstance(item, dict)]

    def list_part_studios(self, doc_id: str, workspace_id: str) -> list[dict[str, Any]]:
        """Return Part Studio elements from a document workspace."""
        return [
            element
            for element in self.list_elements(doc_id, workspace_id)
            if element.get("elementType") == "PARTSTUDIO"
        ]

    def list_part_studios_typed(
        self,
        doc_id: str,
        workspace_id: str,
    ) -> list[OnshapeElement]:
        """Return Part Studio elements as typed wrappers."""
        return [
            element_from_payload(element)
            for element in self.list_part_studios(doc_id, workspace_id)
        ]

    def export_part_studio(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        save_path: Path,
        *,
        export_format: ExportFormat = ExportFormat.STL,
        options: dict[str, Any] | None = None,
    ) -> Path:
        """Export a Part Studio to disk.

        Stage 6 supports STL and keeps other formats behind the same interface
        so adding STEP/OBJ/etc. is localized later.
        """
        if export_format != ExportFormat.STL:
            return self.export_part_studio_translation(
                doc_id,
                workspace_id,
                element_id,
                save_path,
                export_format=export_format,
                options=options,
            )
        return self.export_part_studio_stl(
            doc_id,
            workspace_id,
            element_id,
            save_path,
            options=options,
        )

    def export_part_studio_stl(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        save_path: Path,
        *,
        options: dict[str, Any] | None = None,
    ) -> Path:
        """Download a Part Studio as STL.

        Onshape redirects STL downloads to a region/CDN host that still needs
        authentication. ``requests`` drops auth on cross-host redirects, so this
        follows redirects manually and re-sends credentials, matching the
        proof-of-concept.
        """
        params = stl_export_params(options)
        response = self.api_get(
            f"/partstudios/d/{doc_id}/w/{workspace_id}/e/{element_id}/stl",
            headers=OCTET_STREAM_HEADERS,
            params=params,
            allow_redirects=False,
        )

        data: bytes | None = None
        if response.status_code in REDIRECT_STATUSES:
            cdn_url = response.headers.get("Location") or response.headers.get("location")
            if not cdn_url:
                raise OnshapeApiError("STL export redirect did not include a Location header.")
            redirected = self.api_get(
                cdn_url,
                headers=OCTET_STREAM_HEADERS,
                timeout=self.retry_policy.export_timeout_seconds,
            )
            data = self._validated_export_bytes(
                redirected,
                "redirected STL download",
                min_bytes=MIN_STL_BYTES + 1,
            )
        else:
            data = self._validated_export_bytes(
                response,
                "STL export",
                min_bytes=MIN_STL_BYTES + 1,
            )

        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(data)
        return save_path

    def export_part_studio_translation(
        self,
        doc_id: str,
        workspace_id: str,
        element_id: str,
        save_path: Path,
        *,
        export_format: ExportFormat,
        options: dict[str, Any] | None = None,
    ) -> Path:
        """Export STEP/OBJ and other translation-backed Part Studio formats."""
        if export_format == ExportFormat.STEP:
            endpoint = f"/partstudios/d/{doc_id}/w/{workspace_id}/e/{element_id}/export/step"
            body = step_export_body(save_path.name, options)
        elif export_format == ExportFormat.OBJ:
            endpoint = f"/partstudios/d/{doc_id}/w/{workspace_id}/e/{element_id}/export/obj"
            body = obj_export_body(save_path.name, options)
        else:
            endpoint = f"/partstudios/d/{doc_id}/w/{workspace_id}/e/{element_id}/translations"
            body = generic_translation_body(save_path.name, export_format, options)

        create_response = self.api_post(endpoint, headers=JSON_HEADERS, json=body)
        self._raise_for_status_code(create_response, "create Part Studio translation", {200, 201})
        info = self._require_json_object(create_response, "translation creation")
        translation_id = str(info.get("id") or "")
        if not translation_id:
            raise OnshapeApiError("Translation response did not include an id.")

        completed = self.wait_for_translation(translation_id)
        external_ids = completed.get("resultExternalDataIds")
        if not isinstance(external_ids, list) or not external_ids:
            raise OnshapeApiError("Completed translation did not include external data ids.")

        result_doc_id = str(completed.get("documentId") or completed.get("resultDocumentId") or doc_id)
        return self.download_external_data(result_doc_id, str(external_ids[0]), save_path)

    def wait_for_translation(self, translation_id: str) -> dict[str, Any]:
        """Poll a translation request until it is done or failed."""
        deadline = time.monotonic() + self.retry_policy.translation_timeout_seconds
        while True:
            response = self.api_get(f"/translations/{translation_id}", headers=JSON_HEADERS)
            self._raise_for_status(response, f"fetch translation {translation_id}")
            info = self._require_json_object(response, f"translation {translation_id}")
            state = info.get("requestState")
            if state == "DONE":
                return info
            if state == "FAILED":
                reason = info.get("failureReason") or "unknown failure"
                raise OnshapeApiError(f"Translation {translation_id} failed: {reason}")
            if time.monotonic() >= deadline:
                raise OnshapeApiError(f"Translation {translation_id} timed out.")
            self.sleep_fn(self.retry_policy.translation_poll_interval_seconds)

    def download_external_data(self, doc_id: str, file_id: str, save_path: Path) -> Path:
        """Download a translated external-data file to disk."""
        response = self.api_get(
            f"/documents/d/{doc_id}/externaldata/{file_id}",
            headers=OCTET_STREAM_HEADERS,
            allow_redirects=False,
            timeout=self.retry_policy.export_timeout_seconds,
        )
        data = self._download_bytes_following_redirects(response, "external data download")
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(data)
        return save_path

    def _normalize_url(self, url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return urljoin(f"{self.base_url}/", url.lstrip("/"))

    def _should_retry_response(
        self,
        response: requests.Response,
        attempt: int,
        max_attempts: int,
    ) -> bool:
        return (
            attempt < max_attempts - 1
            and self.retry_policy.is_retryable_http_status(response.status_code)
        )

    def _sleep_before_retry(self, response: requests.Response, attempt: int) -> None:
        retry_after = retry_after_delay(response)
        if retry_after is None:
            retry_after = self.retry_policy.delay_for_attempt(attempt)
        self.sleep_fn(retry_after)

    def _record_response(self, response: requests.Response) -> None:
        if self.api_pool is None:
            return
        reset_at = rate_limit_reset_at(response)
        self.api_pool.record_http_result(
            self.account.name,
            response.status_code,
            reset_at=reset_at,
        )

    def _record_exception(self, exc: BaseException) -> None:
        if self.api_pool is not None:
            self.api_pool.record_failure(self.account.name, type(exc).__name__)

    def _require_json_object(
        self,
        response: requests.Response,
        context: str,
    ) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise OnshapeApiError(f"Expected JSON object for {context}.") from exc
        if not isinstance(payload, dict):
            raise OnshapeApiError(f"Expected JSON object for {context}.")
        return payload

    def _raise_for_status(self, response: requests.Response, context: str) -> None:
        self._raise_for_status_code(response, context, {200})

    def _raise_for_status_code(
        self,
        response: requests.Response,
        context: str,
        ok_statuses: set[int],
    ) -> None:
        if response.status_code in ok_statuses:
            return
        message = response.text[:300] if response.text else ""
        raise OnshapeApiError(
            f"Onshape API error during {context}: HTTP {response.status_code} {message}",
            status_code=response.status_code,
        )

    def _validated_export_bytes(
        self,
        response: requests.Response,
        context: str,
        *,
        min_bytes: int = 1,
    ) -> bytes:
        if response.status_code != 200:
            message = response.text[:300] if response.text else ""
            raise OnshapeApiError(
                f"Onshape API error during {context}: HTTP {response.status_code} {message}",
                status_code=response.status_code,
            )
        content = response.content
        if len(content) < min_bytes:
            raise OnshapeApiError(f"Onshape returned an empty export for {context}.")
        return content

    def _download_bytes_following_redirects(
        self,
        response: requests.Response,
        context: str,
    ) -> bytes:
        if response.status_code in REDIRECT_STATUSES:
            location = response.headers.get("Location") or response.headers.get("location")
            if not location:
                raise OnshapeApiError(f"{context} redirect did not include a Location header.")
            redirected = self.api_get(
                location,
                headers=OCTET_STREAM_HEADERS,
                timeout=self.retry_policy.export_timeout_seconds,
            )
            return self._validated_export_bytes(redirected, f"redirected {context}")
        return self._validated_export_bytes(response, context)


def doc_has_label(doc: dict[str, Any], label_id: str) -> bool:
    """Return True if a document payload includes ``label_id``."""
    labels = doc.get("documentLabels")
    if not isinstance(labels, list):
        return False
    return any(isinstance(label, dict) and label.get("id") == label_id for label in labels)


def document_matches_date_range(
    doc: dict[str, Any],
    start_dt: datetime,
    end_dt: datetime,
) -> bool:
    """Return True when a document's modified date is inside the range.

    Documents with no ``modifiedAt`` are included, matching the proof-of-concept.
    """
    modified_at = doc.get("modifiedAt")
    if not modified_at:
        return True
    if not isinstance(modified_at, str):
        return False
    parsed = parse_onshape_datetime(modified_at)
    if parsed is None:
        return False
    return start_dt <= parsed <= end_dt


def parse_onshape_datetime(value: str) -> datetime | None:
    """Parse Onshape ISO datetimes, including trailing ``Z`` UTC values."""
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def document_from_payload(payload: dict[str, Any]) -> OnshapeDocument:
    """Create an ``OnshapeDocument`` wrapper from raw API JSON."""
    doc_id = str(payload.get("id", ""))
    if not doc_id:
        raise OnshapeApiError("Document payload is missing id.")
    return OnshapeDocument(
        id=doc_id,
        name=str(payload.get("name") or doc_id),
        modified_at=parse_onshape_datetime(str(payload["modifiedAt"]))
        if payload.get("modifiedAt")
        else None,
        raw=payload,
    )


def element_from_payload(payload: dict[str, Any]) -> OnshapeElement:
    """Create an ``OnshapeElement`` wrapper from raw API JSON."""
    element_id = str(payload.get("id", ""))
    if not element_id:
        raise OnshapeApiError("Element payload is missing id.")
    return OnshapeElement(
        id=element_id,
        name=str(payload.get("name") or element_id),
        element_type=str(payload.get("elementType") or ""),
        raw=payload,
    )


def retry_after_delay(response: requests.Response) -> float | None:
    """Return retry delay from a Retry-After header, if present."""
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(float(value), 0.0)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        return max((retry_at.astimezone(timezone.utc) - datetime.now(timezone.utc)).total_seconds(), 0.0)


def rate_limit_reset_at(response: requests.Response) -> datetime | None:
    """Parse common rate-limit reset headers from an API response."""
    retry_after = retry_after_delay(response)
    if retry_after is not None:
        return datetime.now(timezone.utc) + timedelta(seconds=retry_after)

    for header_name in ("X-Rate-Limit-Reset", "X-RateLimit-Reset"):
        value = response.headers.get(header_name)
        if not value:
            continue
        try:
            numeric = float(value)
        except ValueError:
            try:
                parsed = parsedate_to_datetime(value)
            except (TypeError, ValueError):
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        if numeric > 10_000_000:
            return datetime.fromtimestamp(numeric, tz=timezone.utc)
        return datetime.now(timezone.utc) + timedelta(seconds=numeric)
    return None


def stl_export_params(options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return STL export query parameters with proof-of-concept defaults."""
    params: dict[str, Any] = {"mode": "binary", "units": "millimeter"}
    if options:
        params.update(options)
    return params


def step_export_body(destination_name: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the official STEP async export request body."""
    body: dict[str, Any] = {
        "destinationName": destination_name,
        "storeInDocument": False,
        "triggerAutoDownload": False,
        "notifyUser": False,
        "stepVersionString": "AP242",
    }
    if options:
        body.update(options)
    body.pop("formatName", None)
    return body


def obj_export_body(destination_name: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the official OBJ async export request body."""
    body: dict[str, Any] = {
        "destinationName": destination_name,
        "storeInDocument": False,
        "triggerAutoDownload": False,
        "notifyUser": False,
    }
    if options:
        body.update(options)
    body.pop("formatName", None)
    return body


def generic_translation_body(
    destination_name: str,
    export_format: ExportFormat,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a generic Part Studio translation body."""
    body: dict[str, Any] = {
        "destinationName": destination_name,
        "formatName": translation_format_name(export_format),
        "storeInDocument": False,
        "triggerAutoDownload": False,
        "notifyUser": False,
    }
    if options:
        body.update(options)
    return body


def translation_format_name(export_format: ExportFormat) -> str:
    """Map internal format values to Onshape translation format names."""
    mapping = {
        ExportFormat.IGES: "IGES",
        ExportFormat.DXF: "DXF",
        ExportFormat.PARASOLID: "PARASOLID",
        ExportFormat.CUSTOM: "CUSTOM",
    }
    return mapping.get(export_format, export_format.value.upper())


# Backwards-compatible private helper name from the proof-of-concept.
_doc_has_label = doc_has_label
