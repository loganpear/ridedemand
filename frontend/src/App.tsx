import { BrowserRouter, Navigate, Route, Routes, Link, useNavigate } from "react-router-dom";
import "./App.css";
import {
  apiAddFunds,
  apiCreateListing,
  apiCreateUser,
  apiLatestReservation,
  apiLogin,
  apiReserve,
  apiSearchListings,
  apiViewBalance,
  apiGetDriverStatus,
  apiSetDriverStatus,
} from "./api/client";
import type { Listing, ReservationSummary } from "./api/client";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";

type AuthState = {
  jwt: string | null;
  username: string | null;
  isDriver: boolean | null;
};

function useAuthState(): [AuthState, (auth: AuthState) => void, () => void] {
  const [auth, setAuth] = useState<AuthState>(() => ({
    jwt: localStorage.getItem("jwt"),
    username: localStorage.getItem("username"),
    isDriver:
      localStorage.getItem("isDriver") === null
        ? null
        : localStorage.getItem("isDriver") === "true",
  }));

  function update(next: AuthState) {
    setAuth(next);
    if (next.jwt) {
      localStorage.setItem("jwt", next.jwt);
    } else {
      localStorage.removeItem("jwt");
    }
    if (next.username) {
      localStorage.setItem("username", next.username);
    } else {
      localStorage.removeItem("username");
    }
    if (next.isDriver === null) {
      localStorage.removeItem("isDriver");
    } else {
      localStorage.setItem("isDriver", String(next.isDriver));
    }
  }

  function logout() {
    update({ jwt: null, username: null, isDriver: null });
  }

  return [auth, update, logout];
}

function AppShell() {
  const [auth, setAuth, logout] = useAuthState();

  useEffect(() => {
    async function refreshDriver() {
      if (!auth.username) return;
      try {
        const res = await apiGetDriverStatus(auth.username);
        if (res.driver === 1 || res.driver === 0) {
          setAuth({
            ...auth,
            isDriver: res.driver === 1,
          });
        }
      } catch {
        // ignore; driver status is optional for UI
      }
    }
    refreshDriver();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth.username]);

  return (
    <BrowserRouter>
      <div className="app">
        <header className="app-header">
          <h1>ridedemand</h1>
          <nav>
            <Link to="/dashboard">Dashboard</Link>
            <Link to="/wallet">Wallet</Link>
            {auth.isDriver && <Link to="/offer">Offer a Ride</Link>}
            <Link to="/find">Find a Ride</Link>
            <Link to="/settings">Settings</Link>
          </nav>
          <div className="auth-status">
            {auth.jwt ? (
              <>
                <span>Signed in as {auth.username}</span>
                <button onClick={logout}>Log out</button>
              </>
            ) : (
              <>
                <Link to="/login">Log in</Link>
                <Link to="/signup">Sign up</Link>
              </>
            )}
          </div>
        </header>

        <main className="app-main">
          <Routes>
            <Route
              path="/"
              element={
                auth.jwt ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />
              }
            />
            <Route
              path="/login"
              element={
                <LoginPage
                  onLoggedIn={(jwt, username) => setAuth({ jwt, username, isDriver: null })}
                />
              }
            />
            <Route path="/signup" element={<SignupPage />} />
            <Route
              path="/dashboard"
              element={
                <RequireAuth auth={auth}>
                  <DashboardPage auth={auth} />
                </RequireAuth>
              }
            />
            <Route
              path="/wallet"
              element={
                <RequireAuth auth={auth}>
                  <WalletPage auth={auth} />
                </RequireAuth>
              }
            />
            <Route
              path="/offer"
              element={
                <RequireAuth auth={auth}>
                  <OfferRidePage auth={auth} />
                </RequireAuth>
              }
            />
            <Route
              path="/find"
              element={
                <RequireAuth auth={auth}>
                  <FindRidePage auth={auth} />
                </RequireAuth>
              }
            />
            <Route
              path="/settings"
              element={
                <RequireAuth auth={auth}>
                  <SettingsPage auth={auth} setAuth={setAuth} />
                </RequireAuth>
              }
            />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

function RequireAuth({
  auth,
  children,
}: {
  auth: AuthState;
  children: React.ReactElement;
}) {
  if (!auth.jwt) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function LoginPage({
  onLoggedIn,
}: {
  onLoggedIn: (jwt: string, username: string | null) => void;
}) {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await apiLogin(username, password);
      if (res.status !== 1) {
        setError("Invalid credentials");
      } else {
        onLoggedIn(res.jwt, username);
        navigate("/dashboard");
      }
    } catch (err) {
      setError("Unable to log in");
    } finally {
      setLoading(false);
    }
  }

  function autofillDemoUser() {
    setUsername("demo");
    setPassword("Password123");
  }

  return (
    <section>
      <h2>Log in</h2>
      {error && <p className="error">{error}</p>}
      <form onSubmit={handleSubmit} className="form">
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Logging in..." : "Log in"}
        </button>
        <button type="button" onClick={autofillDemoUser}>
          Autofill with Test User
        </button>
      </form>
    </section>
  );
}

function SignupPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    username: "",
    email_address: "",
    password: "",
    driver: false,
    deposit: 20,
  });
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setStatus(null);
    try {
      const res = await apiCreateUser(form);
      if (res.status === 1) {
        setStatus("Account created! Redirecting to login...");
        setTimeout(() => navigate("/login"), 1000);
      } else {
        if (res.status === 2) {
          setStatus("That username is already taken.");
        } else if (res.status === 3) {
          setStatus("That email address is already in use.");
        } else if (res.status === 4) {
          setStatus(
            "Password must be 8+ chars, with upper/lowercase and a digit, and not contain your name or username.",
          );
        } else {
          setStatus("Signup failed. Please check your details.");
        }
      }
    } catch {
      setStatus("Unable to sign up right now.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <h2>Sign up</h2>
      {status && <p>{status}</p>}
      <form onSubmit={handleSubmit} className="form">
        <label>
          First name
          <input
            value={form.first_name}
            onChange={(e) => setForm({ ...form, first_name: e.target.value })}
          />
        </label>
        <label>
          Last name
          <input
            value={form.last_name}
            onChange={(e) => setForm({ ...form, last_name: e.target.value })}
          />
        </label>
        <label>
          Username
          <input
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
          />
        </label>
        <label>
          Email
          <input
            type="email"
            value={form.email_address}
            onChange={(e) => setForm({ ...form, email_address: e.target.value })}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </label>
        <label>
          Are you a driver?
          <input
            type="checkbox"
            checked={form.driver}
            onChange={(e) => setForm({ ...form, driver: e.target.checked })}
          />
        </label>
        <label>
          Initial deposit (USD)
          <input
            type="number"
            value={form.deposit}
            onChange={(e) => setForm({ ...form, deposit: Number(e.target.value) })}
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Signing up..." : "Create account"}
        </button>
      </form>
    </section>
  );
}

function DashboardPage({ auth }: { auth: AuthState }) {
  const [reservation, setReservation] = useState<ReservationSummary | null>(null);
  const [balance, setBalance] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!auth.jwt) return;
      setLoading(true);
      setError(null);
      try {
        const [resv, bal] = await Promise.all([
          apiLatestReservation(auth.jwt),
          apiViewBalance(auth.jwt),
        ]);
        if (resv.status === 1 && resv.data) {
          setReservation(resv.data);
        }
        if (bal.status === 1) {
          setBalance(bal.balance);
        }
      } catch {
        setError("Unable to load summary");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [auth.jwt]);

  return (
    <section>
      <h2>Dashboard</h2>
      {loading && <p>Loading...</p>}
      {error && <p className="error">{error}</p>}
      {balance && <p>Current balance: ${balance}</p>}
      {reservation ? (
        <div className="card">
          <h3>Latest reservation</h3>
          <p>
            With {reservation.user} on {reservation.ride_date} at {reservation.ride_time}
          </p>
          <p>Price: ${reservation.price}</p>
          <p>Rating: {reservation.rating}</p>
          <p>Status: {reservation.status}</p>
        </div>
      ) : (
        <p>No reservations yet.</p>
      )}
    </section>
  );
}

function WalletPage({ auth }: { auth: AuthState }) {
  const [balance, setBalance] = useState<string | null>(null);
  const [amount, setAmount] = useState(10);
  const [message, setMessage] = useState<string | null>(null);

  async function refresh() {
    if (!auth.jwt) return;
    const res = await apiViewBalance(auth.jwt);
    if (res.status === 1) {
      setBalance(res.balance);
    }
  }

  useEffect(() => {
    refresh();
  }, [auth.jwt]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    if (!auth.jwt) return;
    const res = await apiAddFunds(auth.jwt, amount);
    if (res.status === 1) {
      setMessage("Funds added.");
      await refresh();
    } else {
      setMessage("Unable to add funds.");
    }
  }

  return (
    <section>
      <h2>Wallet</h2>
      {balance && <p>Balance: ${balance}</p>}
      {message && <p>{message}</p>}
      <form onSubmit={handleAdd} className="form">
        <label>
          Amount to add (USD)
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
          />
        </label>
        <button type="submit">Add funds</button>
      </form>
    </section>
  );
}

function OfferRidePage({ auth }: { auth: AuthState }) {
  const [rideDate, setRideDate] = useState("");
  const [rideTime, setRideTime] = useState("");
  const [price, setPrice] = useState(9.99);
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!auth.jwt || !auth.username) return;
    const listingid = Date.now(); // simple client-side id
    const res = await apiCreateListing({
      jwt: auth.jwt,
      ride_date: rideDate,
      ride_time: rideTime,
      price,
      listingid,
    });
    if (res.status === 1) {
      setMessage("Listing created.");
    } else {
      setMessage(res.error || "Unable to create listing.");
    }
  }

  return (
    <section>
      <h2>Offer a ride</h2>
      {message && <p>{message}</p>}
      <form onSubmit={handleSubmit} className="form">
        <label>
          Date
          <input type="date" value={rideDate} onChange={(e) => setRideDate(e.target.value)} />
        </label>
        <label>
          Time
          <input type="time" value={rideTime} onChange={(e) => setRideTime(e.target.value)} />
        </label>
        <label>
          Price (USD)
          <input
            type="number"
            value={price}
            onChange={(e) => setPrice(Number(e.target.value))}
          />
        </label>
        <button type="submit">Create listing</button>
      </form>
    </section>
  );
}

function FindRidePage({ auth }: { auth: AuthState }) {
  const [rideDate, setRideDate] = useState("");
  const [rideTime, setRideTime] = useState("");
  const [results, setResults] = useState<Listing[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!auth.jwt) return;
    const res = await apiSearchListings({
      jwt: auth.jwt,
      ride_date: rideDate,
      ride_time: rideTime || undefined,
    });
    if (res.status === 1 && res.data) {
      setResults(res.data);
      setMessage(null);
    } else {
      setResults([]);
      setMessage(res.error || "No rides found.");
    }
  }

  async function handleReserve(listingid: number) {
    if (!auth.jwt) return;
    const res = await apiReserve(auth.jwt, listingid);
    if (res.status === 1) {
      setMessage("Reservation successful!");
    } else {
      setMessage(res.error || "Unable to reserve.");
    }
  }

  return (
    <section>
      <h2>Find a ride</h2>
      {message && <p>{message}</p>}
      <form onSubmit={handleSearch} className="form">
        <label>
          Date
          <input type="date" value={rideDate} onChange={(e) => setRideDate(e.target.value)} />
        </label>
        <label>
          Time (optional)
          <input type="time" value={rideTime} onChange={(e) => setRideTime(e.target.value)} />
        </label>
        <button type="submit">Search</button>
      </form>

      <ul className="list">
        {results.map((l) => (
          <li key={l.listingid} className="card">
            <p>
              Driver: {l.driver} (rating {l.rating})
            </p>
            <p>Price: ${l.price}</p>
            <button onClick={() => handleReserve(l.listingid)}>Reserve</button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function SettingsPage({
  auth,
  setAuth,
}: {
  auth: AuthState;
  setAuth: (auth: AuthState) => void;
}) {
  const [driver, setDriver] = useState<boolean>(auth.isDriver ?? false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!auth.username) return;
      try {
        const res = await apiGetDriverStatus(auth.username);
        if (res.driver === 1 || res.driver === 0) {
          const isDriver = res.driver === 1;
          setDriver(isDriver);
          setAuth({ ...auth, isDriver });
        }
      } catch {
        // ignore
      }
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth.username]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!auth.jwt || !auth.username) return;
    const res = await apiSetDriverStatus(auth.jwt, auth.username, driver);
    if (res.status === 1) {
      setAuth({ ...auth, isDriver: driver });
      setMessage("Settings saved.");
    } else {
      setMessage("Unable to update settings.");
    }
  }

  return (
    <section>
      <h2>Account settings</h2>
      {message && <p>{message}</p>}
      <form onSubmit={handleSubmit} className="form">
        <div className="card">
          <h3>Role</h3>
          <div className="pill-toggle">
            <button
              type="button"
              className={`pill-option ${driver ? "active" : ""}`}
              onClick={() => setDriver(true)}
            >
              Driver
            </button>
            <button
              type="button"
              className={`pill-option ${!driver ? "active" : ""}`}
              onClick={() => setDriver(false)}
            >
              Rider
            </button>
          </div>
          <p className="muted">Drivers can offer rides; riders can book rides.</p>
        </div>
        <button type="submit">Save</button>
      </form>
    </section>
  );
}

export default AppShell;
