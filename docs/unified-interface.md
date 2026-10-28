# Unified three-agent interface

## Scope and report mapping

Built locally on 27 October 2026 in the existing React/Vite application. Source:
user-confirmed submitted `AIMultiAgentAlcoholRetail_Project-1.pdf`, §1–5, §10.1–10.10,
Figure 3 (overall use cases), Figure 4 (domain structure), Figure 7 (agent boundaries).
These sections and diagrams define three agents and ten core use cases across
five members. They do not restrict the system to vodka. Vodka is the visual focus;
wine and beer remain in the existing shared catalogue.

The visual identity “The Still” and the workspace layout are implementation
choices, not changes to the submitted requirements. The original SVG bottle
illustrations are labelled as illustrations, not real product packaging.

## Routes and integration status

Hash navigation works with the existing FastAPI static mount and supports reload
and browser history. Navigation between operator previews is not authentication.

| Route | Agent / purpose | Use cases |
| --- | --- | --- |
| `/#discover` | Catalogue landing page, search, category filters and product details | Read-only catalogue browsing supporting customer assistance |
| `/#assistant` | CustomerAgent | M1-01 capture; M2-01 rule recommendation; M4-01 budget filter placeholder; availability integration placeholder |
| `/#inventory` | InventoryProcurementAgent | M1-02 stock lookup; M3-01 alerts; M4-02 availability; M5-01 reorder suggestion placeholders |
| `/#insights` | BusinessInsightsAgent | M2-02 existing fixture demo; M3-02 profit margin integration placeholder; M5-02 demand trend placeholder |

No new inventory, budget filtering, profit-margin API, trend analysis or reorder
business logic is claimed. Inventory entries show `Unknown` / `Not connected`;
there are no fabricated stock quantities, dashboard totals or trends. M3 profit
calculation remains an existing backend module awaiting an authenticated API.
Optional features, checkout and supplier ordering remain outside this work.

`GET /api/products` returns the existing `Product` schema through the shared
catalogue loader, with exact decimal strings and no inventory fields. Prices are
labelled catalogue prices with currency unspecified, preserving the existing
contract. Search/category selection only browses catalogue records and does not
implement M4 budget filtering. The vodka entry is displayed first for presentation.

## Design references

- [Dan Murphy’s vodka catalogue](https://www.danmurphys.com.au/spirits/vodka):
  category navigation, catalogue filtering and product-card hierarchy.
- [The Whisky Exchange vodka catalogue](https://www.thewhiskyexchange.com/c/335/vodka):
  curated product presentation and visible bottle specifications.

The application uses its own cream/olive palette, layouts, identity and illustrations;
no retailer logos, photography, reviews, prices or product claims are imported.
Google Fonts provides DM Sans and Playfair Display when reachable; local Arial
and Georgia fallbacks keep the interface usable without external fonts.

## Verification

- Backend: 144 tests passed, including the catalogue API contract.
- Production frontend build passed TypeScript and Vite checks.
- Seven Playwright tests cover capture/reload/errors, recommendations, restocking,
  catalogue category/search/detail/empty states, workspace navigation/history,
  disconnected services, catalogue failure and mobile widths.
- Desktop and 390px mobile screenshots inspected; mobile navigation wraps to
  expose all four page links. Product details support native dialog focus and Escape.
- All functional verification uses fixtures/mocks; zero university model calls.

Run the fixture backend as in README, then open `http://127.0.0.1:8000`.
The local server must restart after the new catalogue API is added; frontend-only
changes need `npm run build` for port 8000 or Vite for development.
