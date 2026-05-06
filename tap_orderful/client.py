"""REST client handling, including OrderfulStream base class."""

from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

import pendulum
from hotglue_singer_sdk.streams import RESTStream
from memoization import cached

from tap_orderful.auth import OrderfulAuthenticator


class OrderfulStream(RESTStream):
    """Orderful stream class (base)."""

    url_base = "https://api.orderful.com/v3/"
    primary_keys = ["id"]
    replication_key = "lastUpdatedAt"
    replication_format = "%Y-%m-%dT%H:%M:%SZ"
    records_jsonpath = "$.data[*]"
    next_page_token_jsonpath = "$.metadata.pagination.links.next"

    @property
    @cached
    def authenticator(self) -> OrderfulAuthenticator:
        """Return a new authenticator object."""
        return OrderfulAuthenticator.create_for_stream(self)

    def get_url_params(
        self, context: Optional[dict], next_page_token: Optional[Any]
    ) -> Dict[str, Any]:
        """Return URL params, extracting cursor from the next-page URL when present."""
        params: dict = {}
        if next_page_token:
            # The Orderful API returns a full URL for the next page cursor.
            # Extract its query params and forward them verbatim.
            parsed = urlparse(str(next_page_token))
            for key, values in parse_qs(parsed.query).items():
                params[key] = values[0] if len(values) == 1 else values
        return params

    def post_process(self, row: dict, context: Optional[dict] = None) -> Optional[dict]:
        """Drop records older than the replication key bookmark.

        The Orderful v3 API has no server-side date filter, so we filter
        client-side after paging through all results.
        """
        if self.replication_key:
            record_value = row.get(self.replication_key)
            if record_value:
                start_time = self.get_starting_time(context)
                if start_time and pendulum.parse(record_value) <= start_time:
                    return None
        return row
