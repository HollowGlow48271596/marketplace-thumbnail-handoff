import base64
import hashlib
import os
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_images import InfraiError, InfraiImages


class SellerAsset(BaseModel):
    product_id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    image_base64: str = Field(min_length=1)


class BuyerUpdate(BaseModel):
    display_shape: Literal["square", "portrait"] = "square"


class ThumbnailRequest(BaseModel):
    order_id: str = Field(min_length=1)
    seller_asset: SellerAsset
    buyer_update: BuyerUpdate


class ThumbnailItem(BaseModel):
    role: str
    width: int
    height: int
    image: dict[str, object]


class OrderHandoff(BaseModel):
    order_id: str
    product_id: str
    display_shape: str
    thumbnails: list[ThumbnailItem]


def thumbnail_plan(display_shape: Literal["square", "portrait"]) -> list[tuple[str, int, int]]:
    listing = (800, 1000) if display_shape == "portrait" else (800, 800)
    return [
        ("listing", *listing),
        ("search", 400, 400),
        ("checkout", 160, 160),
    ]


def get_images() -> InfraiImages:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is required")
    return InfraiImages(api_key)


app = FastAPI(title="Marketplace thumbnail handoff")


@app.post("/orders/thumbnail-handoff", response_model=OrderHandoff)
async def create_handoff(
    request: ThumbnailRequest,
    images: InfraiImages = Depends(get_images),
) -> OrderHandoff:
    try:
        source = base64.b64decode(request.seller_asset.image_base64, validate=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="seller_asset.image_base64 is invalid") from exc

    results: list[ThumbnailItem] = []
    try:
        for role, width, height in thumbnail_plan(request.buyer_update.display_shape):
            identity = f"{request.order_id}:{request.seller_asset.product_id}:{role}:{width}x{height}"
            request_key = hashlib.sha256(identity.encode()).hexdigest()
            image = await images.resize(
                image=source,
                filename=request.seller_asset.filename,
                width=width,
                height=height,
                fit="cover",
                request_key=request_key,
            )
            results.append(ThumbnailItem(role=role, width=width, height=height, image=image))
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail={"code": exc.code, "message": str(exc)}) from exc

    return OrderHandoff(
        order_id=request.order_id,
        product_id=request.seller_asset.product_id,
        display_shape=request.buyer_update.display_shape,
        thumbnails=results,
    )

