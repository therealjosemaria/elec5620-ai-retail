"""Three agent roles and bounded LangGraph handoffs (report Figures 6, 7, 14, 16)."""
from datetime import datetime, timezone
from typing import TypedDict
from uuid import UUID, uuid4

from langgraph.graph import END, START, StateGraph
from pydantic import Field

from backend.availability import ProductAvailabilityResult
from backend.budget_filter import BudgetFilterError, BudgetFilterResult
from backend.models import CustomerRequest, DomainModel, Product
from backend.profit_margin import ProfitMarginResult
from backend.replenishment import InventoryDecisionResult
from backend.demand import DemandResult
from backend.recommendation_store import RecommendationError, SavedRecommendations
from backend.servings import servings_per_package
from backend.restocking import (RestockingOutcome, RestockingResult, RestockingScope,
                                analyse_restocking)


class AgentEvent(DomainModel):
    sender: str
    receiver: str
    operation: str
    status: str
    product_ids: list[str] = Field(default_factory=list)


class WorkflowReport(DomainModel):
    workflow_id: UUID = Field(default_factory=uuid4)
    request_id: UUID | None = None
    kind: str
    outcome: str = "complete"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace: list[AgentEvent] = Field(default_factory=list)
    recommendations: SavedRecommendations | None = None
    budget: BudgetFilterResult | None = None
    availability: list[ProductAvailabilityResult] = Field(default_factory=list)
    restocking: RestockingResult | None = None
    profit: ProfitMarginResult | None = None
    inventory_decision: InventoryDecisionResult | None = None
    demand: DemandResult | None = None
    limitations: list[str] = Field(default_factory=list)


class TracedProfitResult(ProfitMarginResult):
    workflow_id: UUID
    trace: list[AgentEvent]


class TracedRestockingResult(RestockingResult):
    workflow_id: UUID
    trace: list[AgentEvent]


class TracedInventoryResult(InventoryDecisionResult):
    workflow_id: UUID
    trace: list[AgentEvent]


class TracedDemandResult(DemandResult):
    workflow_id: UUID
    trace: list[AgentEvent]


def event(report, sender, receiver, operation, status, ids=()):
    report.trace.append(AgentEvent(sender=sender, receiver=receiver, operation=operation,
                                   status=status, product_ids=list(ids)))


class CustomerState(TypedDict, total=False):
    report: WorkflowReport
    needs: CustomerRequest
    product_ids: list[str]


class CustomerAgent:
    def __init__(self, *, recommend, filter_budget, inventory):
        self.recommend, self.filter_budget, self.inventory = recommend, filter_budget, inventory

    def run(self, request_id, needs):
        def recommend_node(state):
            report = state["report"].model_copy(deep=True)
            try:
                report.recommendations = self.recommend(request_id)
                result = report.recommendations
                report.limitations.extend(line for line in result.limitations
                    if line != "Budget and current availability have not been checked.")
                event(report, "workflow", "customer_agent", "recommend_drinks",
                      "cached" if result.cache_hit else "generated")
                if result.outcome != "complete":
                    report.outcome = "no_match" if result.outcome == "no_match" else "blocked"
                ids = [r.product.product_id for r in result.recommendations]
            except RecommendationError as exc:
                report.outcome, ids = "blocked", []
                report.limitations.append(exc.detail)
                event(report, "workflow", "customer_agent", "recommend_drinks", "failed")
            return {"report": report, "product_ids": ids}

        def budget_node(state):
            report = state["report"].model_copy(deep=True)
            ids = state["product_ids"]
            if state["needs"].budget is None:
                report.outcome = "partial"
                report.limitations.append("Budget is unknown; filtering was not applied.")
                status = "skipped_missing_budget"
            else:
                try:
                    report.budget = self.filter_budget(request_id)
                    ids = [p.product_id for p in report.budget.products]
                    status = report.budget.status.value
                    if not ids:
                        report.outcome = "no_match"
                except BudgetFilterError as exc:
                    report.outcome, ids, status = "blocked", [], "invalid_budget"
                    report.limitations.append(str(exc))
            event(report, "customer_agent", "customer_agent", "apply_budget_filter", status, ids)
            return {"report": report, "product_ids": ids}

        def inventory_node(state):
            report = state["report"].model_copy(deep=True)
            ids = state["product_ids"]
            event(report, "customer_agent", "inventory_procurement_agent", "check_availability", "requested", ids)
            try:
                report.availability = self.inventory(ids)
                status = "returned"
                if any(row.status == "Unknown" for row in report.availability):
                    report.outcome = "partial"
            except (ValueError, RuntimeError) as exc:
                report.outcome, status = "partial", "unavailable"
                report.limitations.append("Inventory evidence is unavailable; availability cannot be confirmed.")
            event(report, "inventory_procurement_agent", "customer_agent", "check_availability", status, ids)
            return {"report": report}

        def finish(state):
            report = state["report"].model_copy(deep=True)
            if report.outcome == "complete" and any("did not resolve" in line for line in report.limitations):
                report.outcome = "partial"
            if report.outcome == "complete" and needs.party_size is not None:
                products = (report.budget.products if report.budget is not None else
                            [row.product for row in report.recommendations.recommendations])
                if needs.party_size <= 0 or any(
                    (capacity := servings_per_package(product)) is None or capacity < needs.party_size
                    for product in products
                ):
                    report.outcome = "partial"
                    report.limitations.append("One package per candidate cannot be confirmed to cover one assumed serving per person; review the package estimates.")
            event(report, "customer_agent", "customer", "present_assistance", report.outcome)
            return {"report": report}

        graph = StateGraph(CustomerState)
        graph.add_node("customer_recommend", recommend_node)
        graph.add_node("customer_budget", budget_node)
        graph.add_node("inventory_availability", inventory_node)
        graph.add_node("customer_present", finish)
        graph.add_edge(START, "customer_recommend")
        graph.add_conditional_edges("customer_recommend", lambda s: "customer_budget" if s["report"].outcome == "complete" else "customer_present")
        graph.add_conditional_edges("customer_budget", lambda s: "inventory_availability" if s["product_ids"] else "customer_present")
        graph.add_edge("inventory_availability", "customer_present")
        graph.add_edge("customer_present", END)
        return graph.compile().invoke({"report": WorkflowReport(kind="customer", request_id=request_id), "needs": needs})["report"]


class BusinessState(TypedDict, total=False):
    report: WorkflowReport
    catalogue: list[Product]
    product_ids: list[str]
    inventory_items: dict


class _InventoryEvidence:
    def __init__(self, items):
        self.items = items

    def lookup_stock(self, product_id):
        value = self.items.get(product_id)
        if value is None:
            raise LookupError("Inventory evidence unavailable.")
        return value.model_copy(deep=True)


class BusinessInsightsAgent:
    def demand(self, analyse):
        def node(state):
            report = state["report"].model_copy(deep=True)
            event(report, "operator", "business_insights_agent", "detect_demand_trends", "requested")
            report.demand = analyse()
            report.outcome = report.demand.outcome
            event(report, "business_insights_agent", "operator", "present_demand_trends", report.outcome)
            return {"report": report}
        graph = StateGraph(BusinessState)
        graph.add_node("business_demand", node)
        graph.add_edge(START, "business_demand")
        graph.add_edge("business_demand", END)
        return graph.compile().invoke({"report": WorkflowReport(kind="demand")})["report"]

    def restock(self, scope: RestockingScope, *, inventory, load_catalogue, load_sales, now):
        def scope_node(state):
            report = state["report"].model_copy(deep=True)
            try:
                products = [Product.model_validate(p) for p in load_catalogue()]
            except Exception:
                products = []
            if (scope.product_id is not None and scope.category is not None) or any(
                v is not None and not v.strip() for v in (scope.product_id, scope.category)):
                chosen = []
            else:
                chosen = [p for p in products if (scope.product_id is None or p.product_id == scope.product_id)
                          and (scope.category is None or p.category.casefold() == scope.category.casefold())]
            if not chosen or len({p.product_id for p in products}) != len(products):
                outcome = RestockingOutcome.INVALID_SCOPE if products else RestockingOutcome.DATA_ERROR
                report.restocking = RestockingResult(outcome=outcome, scope=scope, generated_at=now,
                    limitations=["Scope is invalid or the authorised catalogue is unavailable."])
                report.outcome = outcome.value
            event(report, "operator", "business_insights_agent", "validate_restocking_scope", report.outcome)
            return {"report": report, "catalogue": products, "product_ids": [p.product_id for p in chosen]}

        def inventory_node(state):
            report = state["report"].model_copy(deep=True)
            ids, items = state["product_ids"], {}
            event(report, "business_insights_agent", "inventory_procurement_agent", "lookup_stock", "requested", ids)
            for pid in ids:
                try:
                    items[pid] = inventory.lookup_stock(pid)
                except Exception:
                    items[pid] = None
            event(report, "inventory_procurement_agent", "business_insights_agent", "lookup_stock",
                  "returned" if all(v is not None for v in items.values()) else "incomplete", ids)
            return {"report": report, "inventory_items": items}

        def analyse_node(state):
            report = state["report"].model_copy(deep=True)
            report.restocking = analyse_restocking(scope, authorise=lambda _: True,
                load_catalogue=lambda: state["catalogue"], inventory=_InventoryEvidence(state["inventory_items"]),
                load_sales=load_sales, now=now)
            report.outcome = report.restocking.outcome.value
            event(report, "business_insights_agent", "operator", "present_restocking", report.outcome, state["product_ids"])
            return {"report": report}

        graph = StateGraph(BusinessState)
        graph.add_node("business_scope", scope_node)
        graph.add_node("inventory_evidence", inventory_node)
        graph.add_node("business_analysis", analyse_node)
        graph.add_edge(START, "business_scope")
        graph.add_conditional_edges("business_scope", lambda s: "inventory_evidence" if s["report"].restocking is None else END)
        graph.add_edge("inventory_evidence", "business_analysis")
        graph.add_edge("business_analysis", END)
        return graph.compile().invoke({"report": WorkflowReport(kind="restocking")})["report"]

    def profit(self, analyse):
        def node(state):
            report = state["report"].model_copy(deep=True)
            event(report, "operator", "business_insights_agent", "analyse_profit_margins", "requested")
            report.profit = analyse()
            report.outcome = report.profit.outcome.value
            event(report, "business_insights_agent", "operator", "present_profit_margins", report.outcome)
            return {"report": report}
        graph = StateGraph(BusinessState)
        graph.add_node("business_profit", node)
        graph.add_edge(START, "business_profit")
        graph.add_edge("business_profit", END)
        return graph.compile().invoke({"report": WorkflowReport(kind="profit")})["report"]


class InventoryState(TypedDict, total=False):
    report: WorkflowReport
    evidence: list


def inventory_workflow(*, agent, lookup_request, reorder=False):
    """Figure 15/17: Inventory Agent retrieves evidence then makes its own decision."""
    kind = "reorder" if reorder else "low_stock"
    def lookup(state):
        report = state["report"].model_copy(deep=True)
        event(report, "operator", "inventory_procurement_agent", "review_" + kind, "requested", lookup_request.product_ids)
        event(report, "inventory_procurement_agent", "inventory_query_service", "lookup_stock", "requested", lookup_request.product_ids)
        evidence = agent.lookup_stock(lookup_request)
        event(report, "inventory_query_service", "inventory_procurement_agent", "lookup_stock", "returned", lookup_request.product_ids)
        return {"report": report, "evidence": evidence}
    def decide(state):
        report = state["report"].model_copy(deep=True)
        report.inventory_decision = agent.evaluate_replenishment(state["evidence"], reorder=reorder)
        report.outcome = report.inventory_decision.outcome
        event(report, "inventory_procurement_agent", "operator", "present_" + kind, report.outcome, lookup_request.product_ids)
        return {"report": report}
    graph = StateGraph(InventoryState)
    graph.add_node("inventory_lookup", lookup)
    graph.add_node("inventory_decision", decide)
    graph.add_edge(START, "inventory_lookup")
    graph.add_edge("inventory_lookup", "inventory_decision")
    graph.add_edge("inventory_decision", END)
    return graph.compile().invoke({"report": WorkflowReport(kind=kind)})["report"]
