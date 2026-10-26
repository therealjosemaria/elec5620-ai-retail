"""Traceable cases for UC-M3-02 (report §6.3.2, §10.6). No database or model is used."""
from datetime import date
from decimal import Decimal

import pytest

from backend.models import Product
from backend.profit_margin import AnalysisOutcome, ProfitMarginScope, analyse_profit_margin

TODAY = date(2026, 10, 26)
CATALOGUE = [
    Product(product_id="p1", name="Shiraz", category="Wine", price=Decimal("25.00"),
            abv=Decimal("14.5"), sweetness="dry"),
    Product(product_id="p2", name="Pinot Noir", category="Wine", price=Decimal("30.00"),
            abv=Decimal("13"), sweetness="dry"),
    Product(product_id="p3", name="Lager", category="Beer", price=Decimal("5.00"),
            abv=Decimal("4.5"), sweetness="dry"),
]


def sale(product_id, sale_date, quantity, selling_price, cost, **extra):
    return dict(product_id=product_id, sale_date=sale_date, quantity=quantity,
                selling_price=selling_price, cost=cost, **extra)


# sale_id stands in for data-source columns outside the SalesRecord contract.
SALES = [
    sale("p1", "2026-09-01", 2, "25.00", "15.00", sale_id=1),
    sale("p1", "2026-09-15", 1, "24.50", "15.00", sale_id=2),
    sale("p2", "2026-09-10", 3, "30.00", "21.00", sale_id=3),
    sale("p3", "2026-09-12", 10, "5.00", "3.20", sale_id=4),
    sale("p3", "2026-10-02", 4, "5.00", "3.20", sale_id=5),
]
SEPTEMBER = dict(start_date=date(2026, 9, 1), end_date=date(2026, 9, 30))


def analyse(sales=SALES, **scope):
    return analyse_profit_margin(ProfitMarginScope(**scope), lambda: sales, lambda: CATALOGUE, today=TODAY)


@pytest.mark.parametrize("scope,figures,count", [
    (dict(product_id="p1"), ("74.50", "45.00", "29.50", "39.60"), 2),
    (dict(category="wine"), ("164.50", "108.00", "56.50", "34.35"), 3),
    (SEPTEMBER, ("214.50", "140.00", "74.50", "34.73"), 4),
    (dict(category="Beer", start_date=date(2026, 10, 1), end_date=date(2026, 10, 25)),
     ("20.00", "12.80", "7.20", "36.00"), 1),
])
def test_main_flow_exact_figures_for_each_scope(scope, figures, count):
    result = analyse(**scope)
    assert result.outcome == AnalysisOutcome.COMPLETE
    assert (result.revenue, result.total_cost, result.profit,
            result.profit_margin_percent) == tuple(map(Decimal, figures))
    assert result.record_count == len(result.analysed_records) == count
    assert result.limitations == []


def test_result_states_scope_and_basis_with_decimal_strings():
    body = analyse(product_id="p1", **SEPTEMBER).model_dump(mode="json")
    assert body["scope"] == {"product_id": "p1", "category": None,
                             "start_date": "2026-09-01", "end_date": "2026-09-30"}
    assert body["revenue"] == "74.50" and body["profit_margin_percent"] == "39.60"
    assert "per-unit" in body["calculation_basis"]


def test_decimal_arithmetic_has_no_float_drift():
    result = analyse(sales=[sale("p1", "2026-09-01", 3, "0.10", "0.07")], product_id="p1")
    assert result.revenue == Decimal("0.30") and result.profit == Decimal("0.09")


def test_margin_rounds_half_up_to_two_places():
    # 0.01 / 200.00 is exactly 0.005%.
    result = analyse(sales=[sale("p1", "2026-09-01", 1, "200.00", "199.99")], product_id="p1")
    assert result.profit_margin_percent == Decimal("0.01")


def test_date_only_scope_does_not_need_catalogue():
    def unavailable():
        raise ConnectionError("catalogue offline")
    result = analyse_profit_margin(ProfitMarginScope(**SEPTEMBER), lambda: SALES, unavailable, today=TODAY)
    assert result.outcome == AnalysisOutcome.COMPLETE and result.record_count == 4


@pytest.mark.parametrize("scope", [
    {},
    dict(product_id="p1", category="Wine"),
    dict(start_date=date(2026, 9, 1)),
    dict(start_date=date(2026, 9, 30), end_date=date(2026, 9, 1)),
    dict(start_date=date(2026, 10, 1), end_date=TODAY),
    dict(product_id="p404"),
    dict(category="Cider"),
])
def test_2a_invalid_scope_rejected_without_reading_sales(scope):
    reads = []
    result = analyse_profit_margin(ProfitMarginScope(**scope), lambda: reads.append(1) or SALES,
                                   lambda: CATALOGUE, today=TODAY)
    assert result.outcome == AnalysisOutcome.INVALID_SCOPE
    assert result.revenue is None and result.record_count == 0 and result.limitations
    assert reads == []


def test_3a_missing_cost_excluded_with_coverage_reported():
    result = analyse(sales=SALES + [sale("p1", "2026-09-20", 5, "25.00", None)], product_id="p1")
    assert result.outcome == AnalysisOutcome.PARTIAL
    assert result.revenue == Decimal("74.50")  # The costless sale is not estimated.
    assert result.excluded_missing_cost == 1 and result.record_count == 2
    assert "1 of 3 in-scope records excluded: cost is missing." in result.limitations
    assert "Figures cover 2 of 3 in-scope records." in result.limitations


def test_3a_all_costs_missing_produces_no_figures():
    result = analyse(sales=[sale("p1", "2026-09-01", 2, "25.00", None)], product_id="p1")
    assert result.outcome == AnalysisOutcome.INSUFFICIENT_DATA
    assert (result.revenue, result.total_cost, result.profit, result.profit_margin_percent) == (None,) * 4


@pytest.mark.parametrize("bad", [
    sale("p1", "2026-09-02", 0, "25.00", "15.00"),
    sale("p1", "2026-09-02", 1, "-25.00", "15.00"),
    sale("p1", "2026-09-02", 1, None, "15.00"),
    sale("p1", "2026-09-02", 1, "NaN", "15.00"),
])
def test_invalid_records_excluded_not_repaired(bad):
    result = analyse(sales=SALES + [bad], product_id="p1")
    assert result.outcome == AnalysisOutcome.PARTIAL
    assert result.excluded_invalid == 1 and result.revenue == Decimal("74.50")


def test_records_not_matchable_to_scope_are_reported():
    unmatched = [sale("p404", "2026-09-03", 1, "9.00", "4.00"), sale("p1", None, 1, "25.00", "15.00")]
    result = analyse(sales=SALES + unmatched, category="Wine")
    assert result.outcome == AnalysisOutcome.PARTIAL
    assert result.unassigned == 2 and result.record_count == 3


@pytest.mark.parametrize("broken", ["sales", "catalogue"])
def test_3b_unavailable_source_returns_no_values_or_details(broken, caplog):
    def unavailable():
        raise ConnectionError("PRIVATE connection detail")
    loaders = dict(sales=lambda: SALES, catalogue=lambda: CATALOGUE) | {broken: unavailable}
    result = analyse_profit_margin(ProfitMarginScope(category="Wine"), loaders["sales"],
                                   loaders["catalogue"], today=TODAY)
    assert result.outcome == AnalysisOutcome.SOURCE_UNAVAILABLE
    assert result.revenue is None and result.record_count == 0
    assert "PRIVATE" not in result.model_dump_json() and "PRIVATE" not in caplog.text


def test_4a_no_sales_in_scope_is_explicit():
    result = analyse(product_id="p2", start_date=date(2026, 10, 1), end_date=date(2026, 10, 25))
    assert result.outcome == AnalysisOutcome.NO_DATA
    assert result.revenue is None and result.limitations


def test_zero_revenue_leaves_margin_undefined():
    result = analyse(sales=[sale("p1", "2026-09-01", 1, "0.00", "0.00")], product_id="p1")
    assert result.outcome == AnalysisOutcome.COMPLETE
    assert result.profit == 0 and result.profit_margin_percent is None
    assert "Profit margin is undefined because revenue is zero." in result.limitations


def test_analysis_is_read_only():
    sales = [dict(row) for row in SALES]
    analyse(sales=sales, category="Wine")
    assert sales == SALES
