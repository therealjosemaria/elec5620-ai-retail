# Unified three-agent interface

**28 October integration update:** stock, availability, AUD budget filtering,
profit margins and connected restocking are now wired into these workspaces.
The original table below records the earlier UI implementation; current status
and remaining three unimplemented functions are tracked in `team-status.md`.

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
| `/#assistant` | CustomerAgent | M1-01 capture; M2-01 Qwen recommendations; M4-01 budget; availability handoff and saved communication trace |
| `/#inventory` | InventoryProcurementAgent | Connected M1-02 stock, M3-01 alerts, M4-02 availability and M5-01 reorder |
| `/#insights` | BusinessInsightsAgent | Connected M2-02 restocking, M3-02 profit margins and M5-02 demand trends |

The original Cedar UI has now been connected to the shared services and all ten
core use cases. Unknown/stale evidence remains explicit; no quantities or trends
are invented. Operator tools require the private token. Optional features,
checkout and supplier ordering remain outside the implementation.

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
