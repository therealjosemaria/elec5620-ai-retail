export async function readApi<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Invalid request. Check the selected scope.");
  return data;
}

export type Availability = {
  product_id: string; status: "Available" | "Unavailable" | "Unknown";
  stock_quantity: number | null; last_updated: string | null; reason: string;
};

