import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

  it("shows the landing page again after navigating back from the chatbot dashboard item", async () => {
    window.history.pushState({}, "", "/");
    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: /챗봇으로 시작하기/ }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "정책 챗봇" })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Dashboard/ }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /챗봇으로 시작하기/ })).toBeInTheDocument();
    });

    expect(screen.getByRole("main")).toHaveClass("opacity-100");
  });
});
