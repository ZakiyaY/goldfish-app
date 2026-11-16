import { httpClient } from "./httpClient";
import { mockClient } from "./mockClient";
import type { GoldfishApi } from "./types";

const useMocks = ((import.meta.env.VITE_USE_MOCKS as string | undefined) ?? "true") !== "false";
export const api: GoldfishApi = useMocks ? mockClient : httpClient;
