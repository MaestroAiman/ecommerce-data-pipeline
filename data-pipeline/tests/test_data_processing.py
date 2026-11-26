from datetime import datetime

import pandas as pd

from data_processing.data_processing import (
    clean_customers,
    clean_products,
    clean_orders,
    clean_order_items,
    clean_reviews,
    compute_customer_metrics,
    compute_product_metrics,
    compute_monthly_sales,
)


def test_clean_customers_normalizes_email_and_assigns_age_group():
    customers = pd.DataFrame([
        {"customer_id": "c1", "email": "  Alice@Example.COM ",
         "date_of_birth": "1990-01-01", "registration_date": "2020-01-01"},
        # malformed email + missing date_of_birth (edge cases)
        {"customer_id": "c2", "email": "NOT-AN-EMAIL",
         "date_of_birth": None, "registration_date": "2021-05-01"},
    ])

    result = clean_customers(customers)

    assert result.loc[0, "email"] == "alice@example.com"
    # no validation is performed today - a malformed email is still lowered/stripped
    assert result.loc[1, "email"] == "not-an-email"

    expected_age = (datetime.now() - pd.Timestamp("1990-01-01")).days // 365
    assert result.loc[0, "age"] == expected_age
    assert result.loc[0, "age_group"] in ["18-25", "26-35", "36-50", "51-65", "65+"]

    # null date_of_birth -> age/age_group can't be computed, but it doesn't crash
    assert pd.isna(result.loc[1, "age"])
    assert pd.isna(result.loc[1, "age_group"])


def test_clean_products_price_category_boundaries_and_invalid_price():
    products = pd.DataFrame([
        {"product_id": "p1", "product_name": "  Budget Item ", "price": "40"},
        {"product_id": "p2", "product_name": "Mid Item", "price": 100},
        {"product_id": "p3", "product_name": "Premium Item", "price": 300},
        {"product_id": "p4", "product_name": "Luxury Item", "price": 900},
        # non-numeric price (edge case)
        {"product_id": "p5", "product_name": "Bad Price Item", "price": "not-a-number"},
    ])

    result = clean_products(products)

    assert result.loc[0, "product_name"] == "Budget Item"
    assert result.loc[0, "price_category"] == "Budget"
    assert result.loc[1, "price_category"] == "Mid-range"
    assert result.loc[2, "price_category"] == "Premium"
    assert result.loc[3, "price_category"] == "Luxury"

    assert pd.isna(result.loc[4, "price"])
    assert pd.isna(result.loc[4, "price_category"])


def test_clean_orders_and_order_items_handle_nulls():
    orders = pd.DataFrame([
        {"order_id": "o1", "customer_id": "c1", "order_date": "2025-03-15", "total_amount": "99.90"},
        # missing order_date (edge case: invalid/null date)
        {"order_id": "o2", "customer_id": "c1", "order_date": None, "total_amount": "50"},
    ])

    result = clean_orders(orders)

    assert result.loc[0, "order_month"] == 3
    assert result.loc[0, "order_year"] == 2025
    assert pd.isna(result.loc[1, "order_date"])
    assert pd.isna(result.loc[1, "order_month"])

    order_items = pd.DataFrame([
        {"order_item_id": "i1", "order_id": "o1", "product_id": "p1", "quantity": 3, "unit_price": 10.0},
        # missing quantity (edge case: null value)
        {"order_item_id": "i2", "order_id": "o1", "product_id": "p1", "quantity": None, "unit_price": 5.0},
    ])

    items_result = clean_order_items(order_items)

    assert items_result.loc[0, "total_price"] == 30.0
    assert pd.isna(items_result.loc[1, "total_price"])


def test_clean_reviews_rating_category_thresholds_and_null_rating():
    reviews = pd.DataFrame([
        {"review_id": "r1", "product_id": "p1", "rating": 5, "review_date": "2025-01-01"},
        {"review_id": "r2", "product_id": "p1", "rating": 4, "review_date": "2025-01-02"},
        {"review_id": "r3", "product_id": "p1", "rating": 3, "review_date": "2025-01-03"},
        {"review_id": "r4", "product_id": "p1", "rating": 1, "review_date": "2025-01-04"},
        # missing rating (edge case: null value)
        {"review_id": "r5", "product_id": "p1", "rating": None, "review_date": "2025-01-05"},
    ])

    result = clean_reviews(reviews)

    assert result.loc[0, "rating_category"] == "Excellent"
    assert result.loc[1, "rating_category"] == "Good"
    assert result.loc[2, "rating_category"] == "Average"
    assert result.loc[3, "rating_category"] == "Poor"
    # a null rating fails every ">=" comparison and falls through to the final
    # else branch - it is labelled "Poor" rather than left null (pinning current behavior)
    assert result.loc[4, "rating_category"] == "Poor"


def test_compute_customer_metrics_computes_clv():
    customers_clean = pd.DataFrame([
        {"customer_id": "c1", "age_group": "26-35"},
        {"customer_id": "c2", "age_group": "36-50"},
    ])
    orders_clean = pd.DataFrame([
        {"customer_id": "c1", "order_id": "o1", "total_amount": 100.0, "order_date": pd.Timestamp("2025-01-01")},
        {"customer_id": "c1", "order_id": "o2", "total_amount": 50.0, "order_date": pd.Timestamp("2025-02-01")},
        {"customer_id": "c2", "order_id": "o3", "total_amount": 200.0, "order_date": pd.Timestamp("2025-03-01")},
    ])

    result = compute_customer_metrics(customers_clean, orders_clean)

    c1 = result[result["customer_id"] == "c1"].iloc[0]
    assert c1["total_spent"] == 150.0
    assert c1["order_count"] == 2
    assert c1["ave_order_value"] == 75.0
    assert c1["age_group"] == "26-35"

    c2 = result[result["customer_id"] == "c2"].iloc[0]
    assert c2["total_spent"] == 200.0
    assert c2["order_count"] == 1


def test_compute_product_metrics_and_monthly_sales():
    products_clean = pd.DataFrame([
        {"product_id": "p1", "product_name": "Widget", "category": "Tools", "price": 20.0},
    ])
    order_items_clean = pd.DataFrame([
        {"order_id": "o1", "product_id": "p1", "quantity": 2, "total_price": 40.0},
        {"order_id": "o2", "product_id": "p1", "quantity": 1, "total_price": 20.0},
    ])

    product_metrics = compute_product_metrics(products_clean, order_items_clean)
    row = product_metrics.iloc[0]
    assert row["total_quantity_sold"] == 3
    assert row["total_revenue"] == 60.0
    assert row["number_of_orders"] == 2
    assert row["product_name"] == "Widget"

    orders_clean = pd.DataFrame([
        {"order_id": "o1", "order_year": 2025, "order_month": 1, "total_amount": 40.0},
        {"order_id": "o2", "order_year": 2025, "order_month": 1, "total_amount": 20.0},
        {"order_id": "o3", "order_year": 2025, "order_month": 2, "total_amount": 15.0},
    ])

    monthly_sales = compute_monthly_sales(orders_clean)

    jan = monthly_sales[(monthly_sales["order_year"] == 2025) & (monthly_sales["order_month"] == 1)].iloc[0]
    assert jan["total_revenue"] == 60.0
    assert jan["order_count"] == 2

    feb = monthly_sales[(monthly_sales["order_year"] == 2025) & (monthly_sales["order_month"] == 2)].iloc[0]
    assert feb["total_revenue"] == 15.0
    assert feb["order_count"] == 1
