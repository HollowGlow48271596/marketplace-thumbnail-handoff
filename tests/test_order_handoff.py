import asyncio
import json

import httpx

from marketplace_thumbnails.infrai_images import InfraiImages
from marketplace_thumbnails.order_handoff import thumbnail_plan


def test_portrait_buyer_update_changes_only_the_listing_crop() -> None:
    plan = thumbnail_plan("portrait")

    assert plan == [
        ("listing", 800, 1000),
        ("search", 400, 400),
        ("checkout", 160, 160),
    ]


def test_image_process_uses_contract_fields() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        text = body.decode("utf-8")
        assert 'name="image"' in text
        assert 'name="ops"' in text
        assert 'name="format"' in text
        assert 'name="idempotency_key"' in text
        assert 'name="store"' in text
        assert 'name="width"' not in text
        assert 'name="height"' not in text
        assert 'name="fit"' not in text
        assert 'name="enlarge"' not in text
        assert json.dumps(
            [{"op": "resize", "width": 800, "height": 1000, "fit": "cover", "enlarge": False}]
        ) in text
        return httpx.Response(200, json={"ok": True, "data": {"id": "result"}})

    async def exercise() -> None:
        images = InfraiImages("test-key", transport=httpx.MockTransport(handler))
        try:
            result = await images.resize(b"image", "product.jpg", 800, 1000, "cover", "request-key")
        finally:
            await images.close()
        assert result == {"id": "result"}

    asyncio.run(exercise())
