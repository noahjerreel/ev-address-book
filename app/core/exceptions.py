"""Domain exceptions raised by the service layer.

The service layer knows nothing about HTTP; ``app.main`` maps these exceptions
to HTTP responses via exception handlers.
"""


class AddressNotFoundError(Exception):
    """Raised when an address with the requested id does not exist."""

    def __init__(self, address_id: int) -> None:
        self.address_id = address_id
        super().__init__(f"Address with id {address_id} not found")
