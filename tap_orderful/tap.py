"""Orderful tap class."""

from typing import List

from hotglue_singer_sdk import Stream, Tap
from hotglue_singer_sdk import typing as th

from tap_orderful.streams import (
    InvoicesStream,
    OrganizationStream,
    PoAcknowledgmentsStream,
    PurchaseOrdersStream,
    RelationshipsStream,
    ShipNoticesStream,
    TransactionsStream,
)

STREAM_TYPES = [
    TransactionsStream,
    PurchaseOrdersStream,
    PoAcknowledgmentsStream,
    ShipNoticesStream,
    InvoicesStream,
    RelationshipsStream,
    OrganizationStream,
]


class TapOrderful(Tap):
    """Orderful tap class."""

    name = "tap-orderful"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_key",
            th.StringType,
            required=True,
            description="Orderful API key (passed as the `orderful-api-key` request header).",
        ),
        th.Property(
            "start_date",
            th.DateTimeType,
            description="The earliest record date to sync (ISO 8601).",
        ),
    ).to_dict()

    def discover_streams(self) -> List[Stream]:
        """Return a list of discovered streams."""
        return [stream_class(tap=self) for stream_class in STREAM_TYPES]


if __name__ == "__main__":
    TapOrderful.cli()
