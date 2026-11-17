import type { components } from "./schema";

export type S = components["schemas"];
export type AssetRow = S["AssetRow"];
export type AssetDetail = S["AssetDetail"];
export type AssetHistory = S["AssetHistory"];
export type RuleResult = S["RuleResult"];
export type Dashboard = S["DashboardOut"];
export type Portfolio = S["PortfolioOut"];
export type ProfileOut = S["ProfileOut"];
export type Question = S["Question"];
export type Plan = S["PlanOut"];
export type FixedIncome = S["FixedIncomeOut"];
export type FixedIncomeIn = S["FixedIncomeIn"];
export type Treasury = S["TreasuryOut"];
export type Compare = S["CompareOut"];
export type Transaction = S["TransactionOut"];
export type TransactionIn = S["TransactionIn"];
export type RuleConfigItem = S["RuleConfigItem"];
export type AllocationItem = S["AllocationItem"];
export type SyncStatus = S["SyncStatus"];

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

type ErrorBody = { detail?: unknown };

function errorMessage(body: ErrorBody, status: number): string {
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) return body.detail.map((d: { msg: string }) => d.msg).join("; ");
  return `Erro ${status}`;
}

async function readErrorBody(res: Response): Promise<ErrorBody> {
  try {
    return (await res.json()) as ErrorBody;
  } catch {
    return {};
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, "Não consegui falar com a API. Ela está rodando? (make dev ou docker compose up)");
  }
  if (!res.ok) throw new ApiError(res.status, errorMessage(await readErrorBody(res), res.status));
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(body ?? {}) }),
  put: <T>(path: string, body: unknown) => request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  del: (path: string) => request<void>(path, { method: "DELETE" }),
};
