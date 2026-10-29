"""End-to-end tests for the ``/addresses`` endpoints."""

from typing import Any

import pytest
from fastapi.testclient import TestClient


def _create(client: TestClient, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post("/addresses", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------- #
# Create / read
# --------------------------------------------------------------------------- #
def test_create_address(client: TestClient, address_payload: dict[str, Any]) -> None:
    body = _create(client, address_payload)

    assert body["id"] >= 1
    assert body["country"] == "DE"  # normalised to upper case
    assert body["latitude"] == address_payload["latitude"]
    assert body["created_at"].endswith("Z")  # serialised as UTC
    assert "updated_at" in body


def test_get_address(client: TestClient, address_payload: dict[str, Any]) -> None:
    created = _create(client, address_payload)

    response = client.get(f"/addresses/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_missing_address_returns_404(client: TestClient) -> None:
    response = client.get("/addresses/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Address with id 999 not found"}


def test_list_addresses_with_pagination(
    client: TestClient, address_payload: dict[str, Any]
) -> None:
    ids = [_create(client, {**address_payload, "label": f"#{i}"})["id"] for i in range(3)]

    assert [a["id"] for a in client.get("/addresses").json()] == ids
    assert [a["id"] for a in client.get("/addresses?offset=1&limit=1").json()] == ids[1:2]


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("latitude", 90.1),
        ("latitude", -91),
        ("longitude", 180.5),
        ("longitude", "east"),
        ("country", "DEU"),
        ("postal_code", "10117!"),
        ("street", "   "),  # blank after stripping whitespace
        ("city", ""),
    ],
)
def test_create_rejects_invalid_values(
    client: TestClient, address_payload: dict[str, Any], field: str, value: Any
) -> None:
    response = client.post("/addresses", json={**address_payload, field: value})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == field


def test_create_rejects_missing_coordinates(
    client: TestClient, address_payload: dict[str, Any]
) -> None:
    payload = {k: v for k, v in address_payload.items() if k != "latitude"}

    assert client.post("/addresses", json=payload).status_code == 422


def test_create_rejects_unknown_fields(
    client: TestClient, address_payload: dict[str, Any]
) -> None:
    response = client.post("/addresses", json={**address_payload, "foo": "bar"})

    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Update / delete
# --------------------------------------------------------------------------- #
def test_patch_updates_only_given_fields(
    client: TestClient, address_payload: dict[str, Any]
) -> None:
    created = _create(client, address_payload)

    response = client.patch(f"/addresses/{created['id']}", json={"city": "Potsdam"})

    assert response.status_code == 200
    body = response.json()
    assert body["city"] == "Potsdam"
    assert body["street"] == created["street"]


def test_patch_can_clear_label(client: TestClient, address_payload: dict[str, Any]) -> None:
    created = _create(client, address_payload)

    response = client.patch(f"/addresses/{created['id']}", json={"label": None})

    assert response.status_code == 200
    assert response.json()["label"] is None


@pytest.mark.parametrize("payload", [{}, {"city": None}, {"latitude": 100}])
def test_patch_rejects_invalid_payload(
    client: TestClient, address_payload: dict[str, Any], payload: dict[str, Any]
) -> None:
    created = _create(client, address_payload)

    assert client.patch(f"/addresses/{created['id']}", json=payload).status_code == 422


def test_put_replaces_address(client: TestClient, address_payload: dict[str, Any]) -> None:
    created = _create(client, address_payload)
    replacement = {**address_payload, "label": None, "city": "Hamburg", "postal_code": "20095"}

    response = client.put(f"/addresses/{created['id']}", json=replacement)

    assert response.status_code == 200
    assert response.json()["city"] == "Hamburg"
    assert response.json()["label"] is None


def test_update_missing_address_returns_404(
    client: TestClient, address_payload: dict[str, Any]
) -> None:
    assert client.patch("/addresses/999", json={"city": "X"}).status_code == 404
    assert client.put("/addresses/999", json=address_payload).status_code == 404


def test_delete_address(client: TestClient, address_payload: dict[str, Any]) -> None:
    created = _create(client, address_payload)

    assert client.delete(f"/addresses/{created['id']}").status_code == 204
    assert client.get(f"/addresses/{created['id']}").status_code == 404
    assert client.delete(f"/addresses/{created['id']}").status_code == 404


# --------------------------------------------------------------------------- #
# Distance search
# --------------------------------------------------------------------------- #
@pytest.fixture
def berlin_and_paris(client: TestClient, address_payload: dict[str, Any]) -> None:
    _create(client, address_payload)  # Brandenburg Gate
    _create(
        client,
        {**address_payload, "label": "Alexanderplatz", "latitude": 52.521918,
         "longitude": 13.413215},
    )
    _create(
        client,
        {**address_payload, "label": "Eiffel Tower", "street": "Champ de Mars",
         "postal_code": "75007", "city": "Paris", "country": "FR",
         "latitude": 48.858370, "longitude": 2.294481},
    )


@pytest.mark.usefixtures("berlin_and_paris")
def test_nearby_returns_addresses_within_distance_sorted(client: TestClient) -> None:
    # Search from Alexanderplatz with a 5 km radius.
    response = client.get(
        "/addresses/nearby", params={"latitude": 52.5219, "longitude": 13.4132, "distance_km": 5}
    )

    assert response.status_code == 200
    body = response.json()
    assert [a["label"] for a in body] == ["Alexanderplatz", "Brandenburg Gate"]
    assert body[0]["distance_km"] < body[1]["distance_km"] <= 5


@pytest.mark.usefixtures("berlin_and_paris")
def test_nearby_large_radius_includes_far_addresses(client: TestClient) -> None:
    response = client.get(
        "/addresses/nearby", params={"latitude": 52.52, "longitude": 13.40, "distance_km": 1000}
    )

    assert {a["city"] for a in response.json()} == {"Berlin", "Paris"}


@pytest.mark.usefixtures("berlin_and_paris")
def test_nearby_respects_limit(client: TestClient) -> None:
    response = client.get(
        "/addresses/nearby",
        params={"latitude": 52.52, "longitude": 13.40, "distance_km": 1000, "limit": 1},
    )

    assert len(response.json()) == 1


def test_nearby_across_antimeridian(
    client: TestClient, address_payload: dict[str, Any]
) -> None:
    _create(client, {**address_payload, "latitude": -16.5, "longitude": 179.9})

    response = client.get(
        "/addresses/nearby",
        params={"latitude": -16.5, "longitude": -179.9, "distance_km": 50},
    )

    assert len(response.json()) == 1
    assert response.json()[0]["distance_km"] < 25


@pytest.mark.parametrize(
    "params",
    [
        {"latitude": 52.5, "longitude": 13.4},  # distance missing
        {"latitude": 52.5, "longitude": 13.4, "distance_km": 0},
        {"latitude": 52.5, "longitude": 13.4, "distance_km": -1},
        {"latitude": 95, "longitude": 13.4, "distance_km": 1},
        {"latitude": 52.5, "longitude": 13.4, "distance_km": 1, "limit": 0},
    ],
)
def test_nearby_rejects_invalid_query(client: TestClient, params: dict[str, Any]) -> None:
    assert client.get("/addresses/nearby", params=params).status_code == 422


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
