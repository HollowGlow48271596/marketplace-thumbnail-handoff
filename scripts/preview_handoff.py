import base64
import json
import sys
from pathlib import Path

import httpx


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Run: python scripts/preview_handoff.py path/to/product.jpg")
    image_path = Path(sys.argv[1])
    payload = {
        "order_id": "order-demo-1042",
        "seller_asset": {
            "product_id": "linen-shirt-blue",
            "filename": image_path.name,
            "image_base64": base64.b64encode(image_path.read_bytes()).decode("ascii"),
        },
        "buyer_update": {"display_shape": "portrait"},
    }
    response = httpx.request(
        method="POST",
        url="http://127.0.0.1:8000/orders/thumbnail-handoff",
        json=payload,
        timeout=60.0,
    )
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()

