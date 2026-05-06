"""Orderful Authentication."""

from hotglue_singer_sdk.authenticators import SimpleAuthenticator


class OrderfulAuthenticator(SimpleAuthenticator):
    """Authenticator for Orderful API key."""

    @classmethod
    def create_for_stream(cls, stream) -> "OrderfulAuthenticator":
        return cls(
            stream=stream,
            auth_headers={"orderful-api-key": stream.config["api_key"]},
        )
