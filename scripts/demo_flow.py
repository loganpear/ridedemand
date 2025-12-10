"""
End‑to‑end smoke test for the ridedemand microservices.

This script assumes you have `docker compose up` running and the services
available on the ports defined in compose.yaml (9000‑9003).

It performs the following high‑level flow:
1. Create a driver and a rider via the user service.
2. Log the rider in and add funds to their wallet.
3. Log the driver in and create an availability listing.
4. Log the rider in again, search for that listing, and reserve it.
5. Print out the final balances for both users.
"""

import os
from dataclasses import dataclass

import requests

USER_BASE = "http://localhost:9000"
AVAIL_BASE = "http://localhost:9001"
RES_BASE = "http://localhost:9002"
PAY_BASE = "http://localhost:9003"


@dataclass
class UserCreds:
	username: str
	password: str
	jwt: str | None = None


def create_user(username: str, password: str, driver: bool, deposit: float) -> UserCreds:
	role_str = "true" if driver else "false"
	resp = requests.post(
		f"{USER_BASE}/create_user",
		data={
			"first_name": "Test",
			"last_name": "User",
			"username": username,
			"email_address": f"{username}@example.com",
			"driver": role_str,
			"deposit": str(deposit),
			"password": password,
			"salt": "static-salt",
		},
		timeout=5,
	)
	print("create_user", username, resp.text)
	return UserCreds(username=username, password=password)


def login(user: UserCreds) -> None:
	resp = requests.post(
		f"{USER_BASE}/login",
		data={"username": user.username, "password": user.password},
		timeout=5,
	)
	print("login", user.username, resp.text)
	data = resp.json()
	if data.get("status") == 1:
		user.jwt = data["jwt"]


def add_funds(user: UserCreds, amount: float) -> None:
	assert user.jwt, "JWT required to add funds"
	resp = requests.post(
		f"{PAY_BASE}/add",
		data={"amount": str(amount)},
		headers={"Authorization": user.jwt},
		timeout=5,
	)
	print("add funds", user.username, resp.text)


def view_balance(user: UserCreds) -> None:
	assert user.jwt, "JWT required to view balance"
	resp = requests.get(
		f"{PAY_BASE}/view",
		headers={"Authorization": user.jwt},
		timeout=5,
	)
	print("view balance", user.username, resp.text)


def create_listing(driver: UserCreds, listing_id: int, ride_date: str, ride_time: str, price: float) -> None:
	assert driver.jwt, "JWT required to create listing"
	resp = requests.post(
		f"{AVAIL_BASE}/listing",
		data={
			"ride_date": ride_date,
			"ride_time": ride_time,
			"price": str(price),
			"listingid": str(listing_id),
		},
		headers={"Authorization": driver.jwt},
		timeout=5,
	)
	print("create listing", resp.text)


def search_listings(rider: UserCreds, ride_date: str) -> list[dict]:
	assert rider.jwt, "JWT required to search listings"
	resp = requests.get(
		f"{AVAIL_BASE}/search",
		params={"ride_date": ride_date},
		headers={"Authorization": rider.jwt},
		timeout=5,
	)
	print("search listings", resp.text)
	data = resp.json()
	return data.get("data", [])


def reserve_listing(rider: UserCreds, listing_id: int) -> None:
	assert rider.jwt, "JWT required to reserve"
	resp = requests.post(
		f"{RES_BASE}/reserve",
		data={"listingid": str(listing_id)},
		headers={"Authorization": rider.jwt},
		timeout=5,
	)
	print("reserve", resp.text)


def main() -> None:
	os.environ.setdefault("JWT_SECRET", "local-dev-secret")

	driver = create_user("driver1", "Password123!", driver=True, deposit=0.0)
	rider = create_user("rider1", "Password123!", driver=False, deposit=20.0)

	login(driver)
	login(rider)

	add_funds(rider, 10.0)
	view_balance(rider)

	ride_date = "2025-12-31"
	ride_time = "09:00"
	listing_id = 1
	create_listing(driver, listing_id=listing_id, ride_date=ride_date, ride_time=ride_time, price=9.99)

	listings = search_listings(rider, ride_date=ride_date)
	if listings:
		reserve_listing(rider, listing_id=listings[0]["listingid"])

	view_balance(rider)
	view_balance(driver)


if __name__ == "__main__":
	main()


