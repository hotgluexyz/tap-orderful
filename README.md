# tap-orderful

`tap-orderful` is a Singer tap for [Orderful](https://orderful.com), a cloud-based EDI platform for B2B document exchange.

Built with the [Hotglue Singer SDK](https://github.com/hotgluexyz/HotglueSingerSDK) for Singer Taps.

## Installation

```bash
pip install tap-orderful
```

Or directly from the repository:

```bash
pip install git+https://github.com/hotgluexyz/tap-orderful.git
```

## Configuration

| Field        | Required | Description                                                    |
|--------------|----------|----------------------------------------------------------------|
| `api_key`    | Yes      | Orderful API key (sent as the `orderful-api-key` header).     |
| `start_date` | No       | Earliest record date to sync, ISO 8601 (e.g. `2024-01-01T00:00:00Z`). |

Example `config.json`:

```json
{
  "api_key": "<your-orderful-api-key>",
  "start_date": "2024-01-01T00:00:00Z"
}
```

Run `tap-orderful --about` to see all available configuration options.

## Source Authentication and Authorization

Orderful uses API key authentication. To obtain your key:

1. Log in to [Orderful](https://app.orderful.com).
2. Go to **Settings > API Keys**.
3. Create or copy an existing API key.

The key is passed as a custom request header (`orderful-api-key`) on every API call — not as a Bearer token.

## Supported Streams

| Stream               | Replication Key  | Primary Key      | Description                                                                    |
|----------------------|------------------|------------------|--------------------------------------------------------------------------------|
| `transactions`       | `lastUpdatedAt`  | `id`             | Metadata index for all EDI documents (850, 855, 856, 810, etc.) exchanged with trading partners. |
| `purchase_orders`    | (full table)     | `transaction_id` | Parsed EDI 850 purchase order body for each matching transaction.              |
| `po_acknowledgments` | (full table)     | `transaction_id` | Parsed EDI 855 PO acknowledgment body for each matching transaction.           |
| `ship_notices`       | (full table)     | `transaction_id` | Parsed EDI 856 ship notice / ASN body for each matching transaction.           |
| `invoices`           | (full table)     | `transaction_id` | Parsed EDI 810 invoice body for each matching transaction.                     |
| `relationships`      | `updatedAt`      | `id`             | Trading partner relationships and the transaction types they cover.            |
| `organization`       | (full table)     | `id`             | Current organization details and EDI account ISA IDs.                          |

The EDI message streams (`purchase_orders`, `po_acknowledgments`, `ship_notices`, `invoices`) are child streams of `transactions`. For each transaction, the tap calls `GET /transactions/{id}/message` and emits a record only when the transaction's EDI type matches that stream (e.g. type `850` for `purchase_orders`).

**Note on incremental sync:** The Orderful v3 API does not support server-side date filtering on the `transactions` or `relationships` endpoints. Incremental replication is applied client-side: the tap pages through all results and emits only records newer than the stored bookmark. Full-page fetches are expected on every run.

## Usage

```bash
# Check version
tap-orderful --version

# Show help and config options
tap-orderful --help

# Discover available streams
tap-orderful --config config.json --discover > catalog.json

# Run a full sync
tap-orderful --config config.json --catalog catalog.json

# Run an incremental sync using a saved state
tap-orderful --config config.json --catalog catalog.json --state state.json
```

## Developer Resources

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e .
pip install ruff pytest

# Lint
ruff check .

# Run tests (requires .secrets/config.json)
pytest tap_orderful/tests/
```
