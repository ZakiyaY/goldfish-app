import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { mockClient } from "@/api/mockClient";

const { getFoldersMock, wipeSessionMock } = vi.hoisted(() => ({
  getFoldersMock: vi.fn(),
  wipeSessionMock: vi.fn(),
}));

vi.mock("@/api/client", () => ({
  api: {
    getFolders: getFoldersMock,
    wipeSession: wipeSessionMock,
  },
}));

import { SessionProvider, useSession } from "@/state/session";

function SessionProbe() {
  const { folders, enabledFolders } = useSession();
  return <output data-testid="folder-state">{JSON.stringify({
    ids: folders.map((folder) => folder.id),
    enabled: Object.fromEntries(folders.map((folder) => [folder.id, enabledFolders[folder.id]])),
  })}</output>;
}

describe("data-driven folder session", () => {
  it("keeps the existing mock folders and defaults", async () => {
    const folders = await mockClient.getFolders();

    expect(folders.map((folder) => folder.id)).toEqual(["calendar", "1-1s", "meetings", "inbox", "hr-private"]);
    expect(folders.find((folder) => folder.id === "hr-private")).toMatchObject({
      defaultEnabled: false,
      sensitive: true,
    });
  });

  it("uses the API folder list and each folder's defaultEnabled value", async () => {
    getFoldersMock.mockResolvedValue([
      { id: "Calendar", label: "Calendar", defaultEnabled: true, sensitive: false },
      { id: "People", label: "People", defaultEnabled: true, sensitive: false },
      { id: "HR-private", label: "HR-private", defaultEnabled: false, sensitive: true },
      { id: "Projects", label: "Projects", defaultEnabled: true, sensitive: false },
    ]);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

    render(
      <QueryClientProvider client={queryClient}>
        <SessionProvider date="2026-11-21"><SessionProbe /></SessionProvider>
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(JSON.parse(screen.getByTestId("folder-state").textContent ?? "{}")).toEqual({
        ids: ["Calendar", "People", "HR-private", "Projects"],
        enabled: { Calendar: true, People: true, "HR-private": false, Projects: true },
      });
    });
  });
});
