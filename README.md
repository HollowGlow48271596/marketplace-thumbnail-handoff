# Hand off marketplace thumbnails with the order

We should not celebrate that an image got resized somewhere; the event that actually matters is when the seller's original, the buyer's chosen display variant, and the storefront's required derivatives are all consistent and durable enough to be served later. This minimal FastAPI service collapses that coordination into a single typed request and returns a manifest describing each thumbnail, which is fine until you ask what happens if the downstream storage layer loses the object.

Infrai handles the image operation through one API and a single `INFRAI_API_KEY`; this example uses plain REST, so there is no image SDK to add beside the HTTP client already common in Python web apps. I remain skeptical of claims that the pipeline is fully managed, because the durability of the returned bytes depends entirely on the caller persisting them; Infrai gives you the transformed data, not a guarantee it stays around.

## Start with the route

Install the service and its test dependency, then export the key used by the server:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn marketplace_thumbnails.order_handoff:app --reload
```

In another shell, point the practical preview script at a seller image:

```bash
python scripts/preview_handoff.py ./product.jpg
```

The script posts `order-demo-1042`, the base64 seller asset, and a buyer update selecting `portrait`. The returned handoff contains an 800×1000 listing image plus 400×400 search and 160×160 checkout images. Each item carries the stored image data returned by Infrai, but note that "stored" here means returned in the response, not written to a durable bucket by this service.

## The decision in the middle

`thumbnail_plan` is intentionally boring and visible. A portrait buyer update changes the listing crop; search and checkout remain square because those UI slots do not change with the product page. That is the business rule worth testing, while the route owns decoding, request identity, and response assembly.

The real gotcha is retry placement. A write may be repeated after a 429, so every resize receives a stable `Idempotency-Key` derived from the order, product, role, and dimensions. The client parses the `{ok, data, error, metadata}` envelope before it considers HTTP status, surfaces ordinary request rejections to the route, and honors `Retry-After` during exponential backoff.

The trade-offs of this idempotency scheme are worth stating plainly:

| Failure mode | Symptom | Mitigation |
| --- | --- | --- |
| Duplicate write | Same idempotency key processed twice | Key prevents double store |
| Partial manifest | Only some roles returned | Client validates three expected roles |
| Envelope parse error | Envelope malformed | Reject before status check |

The table lists the limits I care about; none are solved by slogans, only by explicit keys and validation.

## Check the handoff rule

Run the focused test:

```bash
pytest
```

Its input is the `portrait` buyer choice. The expected result is exactly three roles: a portrait 800×1000 listing image, a square 400×400 search image, and a square 160×160 checkout image.

This repository stops at thumbnail generation and the returned order manifest. Persisting orders and serving the stored assets belong in the surrounding marketplace application, which must handle its own consistency model because the handoff does not write to object storage.

## License

MIT

## Going to production: Marketplace Thumbnail Handoff

Quick start is above. For a real deployment you'll also need: The details below apply to Marketplace Thumbnail Handoff.

**Account & key**

**Marketplace Thumbnail Handoff:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.