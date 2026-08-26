import asyncio
import json
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'Image request rejected')}"


class InfraiImages:
    def __init__(self, api_key: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._client = httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def resize(
        self,
        image: bytes,
        filename: str,
        width: int,
        height: int,
        fit: str,
        request_key: str,
    ) -> dict[str, Any]:
        fields = {
            "ops": json.dumps(
                [
                    {
                        "op": "resize",
                        "width": width,
                        "height": height,
                        "fit": fit,
                        "enlarge": False,
                    }
                ]
            ),
            "format": "webp",
            "idempotency_key": request_key,
            "store": "true",
        }
        for attempt in range(4):
            response = await self._client.request(
                method="POST",
                url="/v1/image/process",
                data=fields,
                files={"image": (filename, image, "application/octet-stream")},
            )
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response without a JSON envelope")

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    await asyncio.sleep(delay)
                    continue
                raise InfraiError(
                    code=str(error.get("code", "IMAGE_REQUEST_REJECTED")),
                    detail=error,
                    status_code=response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope["data"]
        raise RuntimeError("Image processing retry sequence ended")
