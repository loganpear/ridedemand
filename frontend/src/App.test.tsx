import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

describe("App shell", () => {
  it("renders login form by default", () => {
    render(<App />);

    // Use the heading to avoid the nav link and button text
    expect(screen.getByRole("heading", { name: /Log in/i })).toBeDefined();
    expect(screen.getByLabelText(/Username/i)).toBeDefined();
  });

  it("shows navigation links", () => {
    render(<App />);

    expect(screen.getByText(/Dashboard/i)).toBeDefined();
    expect(screen.getByText(/Wallet/i)).toBeDefined();
  });
});


