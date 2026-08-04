import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("renders the product entry screen", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "나만 결혼해?" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "정책 탐색 시작" })).toBeInTheDocument();
  });
});
