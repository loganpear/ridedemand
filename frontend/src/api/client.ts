export type ApiResponse<T> = {
  status: number;
  error?: string;
  data?: T;
};

export type LoginResponse = {
  status: number;
  jwt: string;
};

export type Listing = {
  listingid: number;
  price: string;
  driver: string;
  rating: string;
};

export type ReservationSummary = {
  listingid: number;
  price: string;
  user: string;
  rating: string;
  ride_date: string;
  ride_time: string;
  status: string;
};

const USER_BASE = "/api/user";
const AVAIL_BASE = "/api/availability";
const RES_BASE = "/api/reservations";
const PAY_BASE = "/api/payments";

function authHeaders(jwt?: string): HeadersInit {
  return jwt ? { Authorization: jwt } : {};
}

export async function apiLogin(
  username: string,
  password: string,
): Promise<LoginResponse> {
  const body = new URLSearchParams({ username, password });
  const res = await fetch(`${USER_BASE}/login`, {
    method: "POST",
    body,
  });
  if (!res.ok) {
    throw new Error("Network error during login");
  }
  return (await res.json()) as LoginResponse;
}

export async function apiCreateUser(params: {
  first_name: string;
  last_name: string;
  username: string;
  email_address: string;
  driver: boolean;
  deposit: number;
  password: string;
}): Promise<ApiResponse<unknown>> {
  const body = new URLSearchParams({
    first_name: params.first_name,
    last_name: params.last_name,
    username: params.username,
    email_address: params.email_address,
    driver: params.driver ? "true" : "false",
    deposit: params.deposit.toString(),
    password: params.password,
    salt: "frontend-salt",
  });
  const res = await fetch(`${USER_BASE}/create_user`, {
    method: "POST",
    body,
  });
  return (await res.json()) as ApiResponse<unknown>;
}

export type DriverStatusResponse = {
  driver: number | null;
};

export async function apiGetDriverStatus(
  username: string,
): Promise<DriverStatusResponse> {
  const url = new URL(`${USER_BASE}/get_driver_status`, window.location.origin);
  url.searchParams.set("username", username);
  const res = await fetch(url.toString().replace(window.location.origin, ""));
  return (await res.json()) as DriverStatusResponse;
}

export async function apiSetDriverStatus(
  jwt: string,
  username: string,
  driver: boolean,
): Promise<ApiResponse<unknown>> {
  const body = new URLSearchParams({
    username,
    driver: driver ? "true" : "false",
  });
  const res = await fetch(`${USER_BASE}/set_driver_status`, {
    method: "POST",
    headers: authHeaders(jwt),
    body,
  });
  return (await res.json()) as ApiResponse<unknown>;
}

export async function apiViewBalance(
  jwt: string,
): Promise<{ status: number; balance: string }> {
  const res = await fetch(`${PAY_BASE}/view`, {
    headers: authHeaders(jwt),
  });
  return (await res.json()) as { status: number; balance: string };
}

export async function apiAddFunds(
  jwt: string,
  amount: number,
): Promise<ApiResponse<unknown>> {
  const body = new URLSearchParams({
    amount: amount.toString(),
  });
  const res = await fetch(`${PAY_BASE}/add`, {
    method: "POST",
    headers: authHeaders(jwt),
    body,
  });
  return (await res.json()) as ApiResponse<unknown>;
}

export async function apiCreateListing(params: {
  jwt: string;
  ride_date: string;
  ride_time: string;
  price: number;
  listingid: number;
}): Promise<ApiResponse<unknown>> {
  const body = new URLSearchParams({
    ride_date: params.ride_date,
    ride_time: params.ride_time,
    price: params.price.toString(),
    listingid: params.listingid.toString(),
  });
  const res = await fetch(`${AVAIL_BASE}/listing`, {
    method: "POST",
    headers: authHeaders(params.jwt),
    body,
  });
  return (await res.json()) as ApiResponse<unknown>;
}

export async function apiSearchListings(params: {
  jwt: string;
  ride_date: string;
  ride_time?: string;
}): Promise<ApiResponse<Listing[]>> {
  const url = new URL(`${AVAIL_BASE}/search`, window.location.origin);
  url.searchParams.set("ride_date", params.ride_date);
  if (params.ride_time) {
    url.searchParams.set("ride_time", params.ride_time);
  }
  const res = await fetch(url.toString().replace(window.location.origin, ""), {
    headers: authHeaders(params.jwt),
  });
  return (await res.json()) as ApiResponse<Listing[]>;
}

export async function apiReserve(
  jwt: string,
  listingid: number,
): Promise<ApiResponse<unknown>> {
  const body = new URLSearchParams({
    listingid: listingid.toString(),
  });
  const res = await fetch(`${RES_BASE}/reserve`, {
    method: "POST",
    headers: authHeaders(jwt),
    body,
  });
  return (await res.json()) as ApiResponse<unknown>;
}

export async function apiLatestReservation(
  jwt: string,
): Promise<ApiResponse<ReservationSummary>> {
  const res = await fetch(`${RES_BASE}/view`, {
    headers: authHeaders(jwt),
  });
  return (await res.json()) as ApiResponse<ReservationSummary>;
}


