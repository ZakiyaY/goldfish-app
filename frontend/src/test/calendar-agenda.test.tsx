import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { meetings } from "@/api/fixtures";
import { CalendarAgenda } from "@/components/CalendarAgenda";

describe("calendar agenda", () => {
  it("shows three selectable meeting options with readable times", () => {
    const onSelect = vi.fn();
    render(<CalendarAgenda meetings={meetings} selectedId="m1" onSelect={onSelect} />);

    expect(screen.getAllByRole("button")).toHaveLength(3);
    expect(screen.getByRole("button", { name: "9:30am Team standup" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(
      screen.getByRole("button", { name: "11am Roadmap review, brief ready" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "2pm 1:1 with Priya, brief ready" }),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "11am Roadmap review, brief ready" }));
    expect(onSelect).toHaveBeenCalledWith("m2");
  });
});
