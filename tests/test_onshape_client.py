import unittest
from datetime import datetime, timezone
from typing import Any

from onshape_export_manager.core.api_pool import ApiPool
from onshape_export_manager.core import onshape_client as onshape_client_module
from onshape_export_manager.core.models import ExportFormat, OnshapeAccount
from onshape_export_manager.core.onshape_client import (
    OnshapeApiError,
    OnshapeClient,
    RequestRetryPolicy,
    doc_has_label,
)


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        payload: Any = None,
        *,
        text: str = "",
        headers: dict[str, str] | None = None,
        content: bytes = b"",
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}
        self.content = content

    def json(self) -> Any:
        if isinstance(self._payload, BaseException):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, responses: list[Any]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._request("GET", url, kwargs)

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._request("POST", url, kwargs)

    def _request(self, method: str, url: str, kwargs: dict[str, Any]) -> FakeResponse:
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class OnshapeClientTests(unittest.TestCase):
    def account(self) -> OnshapeAccount:
        return OnshapeAccount(name="test", access_key="access", secret_key="secret")

    def client(
        self,
        responses: list[Any],
        *,
        api_pool: ApiPool | None = None,
        sleeps: list[float] | None = None,
        max_attempts: int = 4,
    ) -> tuple[OnshapeClient, FakeSession]:
        session = FakeSession(responses)
        sleep_log = sleeps if sleeps is not None else []
        client = OnshapeClient(
            account=self.account(),
            session=session,  # type: ignore[arg-type]
            retry_policy=RequestRetryPolicy(max_attempts=max_attempts),
            api_pool=api_pool,
            sleep_fn=sleep_log.append,
        )
        return client, session

    def test_api_get_retries_transient_network_error(self) -> None:
        sleeps: list[float] = []
        client, session = self.client(
            [
                onshape_client_module.requests.exceptions.Timeout("slow"),
                FakeResponse(200, {"ok": True}),
            ],
            sleeps=sleeps,
        )

        response = client.api_get("/documents")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(sleeps, [1.0])
        self.assertEqual(session.calls[0][0], "https://cad.onshape.com/api/v6/documents")

    def test_api_get_retries_retryable_http_status(self) -> None:
        sleeps: list[float] = []
        client, session = self.client(
            [
                FakeResponse(503, {"error": "busy"}),
                FakeResponse(200, {"ok": True}),
            ],
            sleeps=sleeps,
        )

        response = client.api_get("/documents")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(sleeps, [1.0])

    def test_fetch_documents_by_label_pages_and_filters_dates(self) -> None:
        label_id = "123456789012345678901234"
        client, session = self.client(
            [
                FakeResponse(
                    200,
                    {
                        "items": [
                            {
                                "id": "doc-1",
                                "name": "Inside",
                                "modifiedAt": "2026-06-25T10:00:00Z",
                                "documentLabels": [{"id": label_id}],
                            },
                            {
                                "id": "doc-2",
                                "name": "No label",
                                "modifiedAt": "2026-06-25T10:00:00Z",
                                "documentLabels": [],
                            },
                        ],
                        "next": "https://cad.onshape.com/api/v6/documents?page=2",
                    },
                ),
                FakeResponse(
                    200,
                    {
                        "items": [
                            {
                                "id": "doc-3",
                                "name": "Outside",
                                "modifiedAt": "2026-06-20T10:00:00Z",
                                "documentLabels": [{"id": label_id}],
                            }
                        ],
                        "next": None,
                    },
                ),
            ]
        )

        docs = client.fetch_documents_by_label(
            label_id,
            "2026-06-25T00:00:00+00:00",
            "2026-06-25T23:59:59+00:00",
        )

        self.assertEqual([doc["id"] for doc in docs], ["doc-1"])
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(session.calls[1][0], "https://cad.onshape.com/api/v6/documents?page=2")

    def test_default_workspace_fetches_document_when_missing(self) -> None:
        client, session = self.client(
            [
                FakeResponse(
                    200,
                    {"id": "doc-1", "defaultWorkspace": {"id": "workspace-1"}},
                )
            ]
        )

        workspace_id = client.get_default_workspace_id({"id": "doc-1"})

        self.assertEqual(workspace_id, "workspace-1")
        self.assertEqual(session.calls[0][0], "https://cad.onshape.com/api/v6/documents/doc-1")

    def test_list_part_studios_filters_elements(self) -> None:
        client, _ = self.client(
            [
                FakeResponse(
                    200,
                    [
                        {"id": "ps-1", "name": "Main", "elementType": "PARTSTUDIO"},
                        {"id": "asm-1", "name": "Assembly", "elementType": "ASSEMBLY"},
                    ],
                )
            ]
        )

        elements = client.list_part_studios("doc-1", "workspace-1")

        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["id"], "ps-1")

    def test_unexpected_json_shape_raises(self) -> None:
        client, _ = self.client([FakeResponse(200, [])])

        with self.assertRaises(OnshapeApiError):
            client.fetch_documents_by_label(
                "123456789012345678901234",
                "2026-06-25T00:00:00+00:00",
                "2026-06-25T23:59:59+00:00",
            )

    def test_429_updates_api_pool_rate_limit_state(self) -> None:
        account = self.account()
        pool = ApiPool([account])
        session = FakeSession(
            [
                FakeResponse(
                    429,
                    {"error": "rate limited"},
                    headers={"Retry-After": "30"},
                )
            ]
        )
        client = OnshapeClient(
            account=account,
            session=session,  # type: ignore[arg-type]
            retry_policy=RequestRetryPolicy(max_attempts=1),
            api_pool=pool,
            sleep_fn=lambda _: None,
        )

        response = client.api_get("/documents")
        state = pool.snapshot()[0]

        self.assertEqual(response.status_code, 429)
        self.assertEqual(state.rate_limit_status, "rate_limited")
        self.assertIsNotNone(state.rate_limited_until)

    def test_doc_has_label_matches_proof_of_concept_behavior(self) -> None:
        self.assertTrue(
            doc_has_label(
                {"documentLabels": [{"id": "123456789012345678901234"}]},
                "123456789012345678901234",
            )
        )
        self.assertFalse(doc_has_label({"documentLabels": None}, "x"))

    def test_export_stl_follows_redirect_with_auth(self) -> None:
        content = b"0" * 100
        client, session = self.client(
            [
                FakeResponse(307, headers={"Location": "https://cad-euw1.onshape.com/file.stl"}),
                FakeResponse(200, content=content),
            ]
        )
        with self.subTest("download"):
            import tempfile
            from pathlib import Path

            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "part.stl"
                saved = client.export_part_studio_stl("doc", "wid", "eid", out)

                self.assertEqual(saved.read_bytes(), content)
                self.assertEqual(saved, out)
        self.assertEqual(session.calls[0][0], "https://cad.onshape.com/api/v6/partstudios/d/doc/w/wid/e/eid/stl")
        self.assertEqual(session.calls[0][1]["params"]["mode"], "binary")
        self.assertEqual(session.calls[1][0], "https://cad-euw1.onshape.com/file.stl")
        self.assertIn("auth", session.calls[1][1])

    def test_export_step_uses_async_translation_and_external_data(self) -> None:
        content = b"ISO-10303-21;"
        client, session = self.client(
            [
                FakeResponse(200, {"id": "translation-1", "requestState": "ACTIVE"}),
                FakeResponse(200, {"id": "translation-1", "requestState": "ACTIVE"}),
                FakeResponse(
                    200,
                    {
                        "id": "translation-1",
                        "requestState": "DONE",
                        "documentId": "doc",
                        "resultExternalDataIds": ["file-1"],
                    },
                ),
                FakeResponse(200, content=content),
            ],
            sleeps=[],
        )
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "part.step"
            saved = client.export_part_studio(
                "doc",
                "wid",
                "eid",
                out,
                export_format=onshape_client_module.ExportFormat.STEP,
            )

            self.assertEqual(saved.read_bytes(), content)
        self.assertEqual(session.calls[0][0], "https://cad.onshape.com/api/v6/partstudios/d/doc/w/wid/e/eid/export/step")
        self.assertEqual(session.calls[0][1]["json"]["destinationName"], "part.step")
        self.assertEqual(session.calls[-1][0], "https://cad.onshape.com/api/v6/documents/d/doc/externaldata/file-1")

    def test_export_iges_uses_generic_translation_and_external_data(self) -> None:
        content = b"IGES data"
        client, session = self.client(
            [
                FakeResponse(200, {"id": "translation-1", "requestState": "ACTIVE"}),
                FakeResponse(
                    200,
                    {
                        "id": "translation-1",
                        "requestState": "DONE",
                        "documentId": "doc",
                        "resultExternalDataIds": ["file-1"],
                    },
                ),
                FakeResponse(200, content=content),
            ],
            sleeps=[],
        )
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "part.iges"
            saved = client.export_part_studio(
                "doc",
                "wid",
                "eid",
                out,
                export_format=ExportFormat.IGES,
            )

            self.assertEqual(saved.read_bytes(), content)
        self.assertEqual(session.calls[0][0], "https://cad.onshape.com/api/v6/partstudios/d/doc/w/wid/e/eid/translations")
        self.assertEqual(session.calls[0][1]["json"]["formatName"], "IGES")
        self.assertEqual(session.calls[0][1]["json"]["destinationName"], "part.iges")


if __name__ == "__main__":
    unittest.main()
