import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("renders the landing route", () => {
    window.history.pushState({}, "", "/");
    render(<App />);

    expect(screen.getByRole("heading", { name: /나만 결혼해/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /챗봇으로 시작하기/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "주요 지원 분야" })).toBeInTheDocument();
  });
});
