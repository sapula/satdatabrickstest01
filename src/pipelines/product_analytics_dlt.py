# Databricks notebook source
# MAGIC %md
# MAGIC # Product Analytics DLT Pipeline
# MAGIC
# MAGIC This pipeline creates tables for product analytics based on orders, lineitem, and part data.
# MAGIC This is claude generated code.

# COMMAND ----------

import dlt
from pyspark.sql.functions import col, sum as _sum, max as _max, date_sub

# COMMAND ----------

catalog_base_nm = dbutils.widgets.text("catalog_base_nm","tpccopy001")
env = dbutils.widgets.text("env", "dev")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze Layer - Raw Data Ingestion

# COMMAND ----------

@dlt.table(
    name="bronze_orders",
    comment="Raw orders data from source",
    table_properties={
        "quality": "bronze",
        "pipelines.autoOptimize.zOrderCols": "o_orderkey,o_orderdate"
    }
)
def bronze_orders():
    """Ingest raw orders data."""
    return spark.table(f"{catalog_base_nm}_{env}.poc.orders")


@dlt.table(
    name="bronze_lineitem",
    comment="Raw lineitem data from source",
    table_properties={
        "quality": "bronze",
        "pipelines.autoOptimize.zOrderCols": "l_orderkey,l_partkey"
    }
)
def bronze_lineitem():
    """Ingest raw lineitem data."""
    return spark.table(f"{catalog_base_nm}_{env}.poc.lineitem")


@dlt.table(
    name="bronze_part",
    comment="Raw part data from source",
    table_properties={
        "quality": "bronze",
        "pipelines.autoOptimize.zOrderCols": "p_partkey"
    }
)
def bronze_part():
    """Ingest raw part data."""
    return spark.table(f"{catalog_base_nm}_{env}.poc.part")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver Layer - Cleaned and Joined Data

# COMMAND ----------

@dlt.table(
    name="silver_order_details",
    comment="Joined order, lineitem, and part data with quality checks",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.zOrderCols": "o_orderdate,l_partkey"
    }
)
@dlt.expect_or_drop("valid_orderkey", "o_orderkey IS NOT NULL")
@dlt.expect_or_drop("valid_partkey", "l_partkey IS NOT NULL")
@dlt.expect_or_drop("valid_quantity", "l_quantity > 0")
def silver_order_details():
    """Join orders, lineitems, and parts with data quality expectations."""
    orders = dlt.read("bronze_orders")
    lineitems = dlt.read("bronze_lineitem")
    parts = dlt.read("bronze_part")

    return (
        orders
        .join(lineitems, orders.o_orderkey == lineitems.l_orderkey, "inner")
        .join(parts, lineitems.l_partkey == parts.p_partkey, "inner")
        .select(
            orders.o_orderkey,
            orders.o_orderdate,
            lineitems.l_partkey,
            lineitems.l_quantity,
            lineitems.l_extendedprice,
            lineitems.l_discount,
            parts.p_name,
            parts.p_mfgr,
            parts.p_brand,
            parts.p_type,
            parts.p_retailprice
        )
    )

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold Layer - Business Aggregates

# COMMAND ----------

@dlt.table(
    name="gold_top_selling_products_last_30_days",
    comment="Top selling products in the last 30 days",
    table_properties={
        "quality": "gold",
        "pipelines.autoOptimize.zOrderCols": "total_sold"
    }
)
def gold_top_selling_products_last_30_days():
    """Calculate top selling products in the last 30 days."""
    order_details = dlt.read("silver_order_details")

    # Get max date
    max_date_df = order_details.agg(_max("o_orderdate").alias("max_date"))
    max_date = max_date_df.collect()[0]["max_date"]

    # Calculate 30 days ago
    cutoff_date = date_sub(max_date, 30)

    # Filter and aggregate
    result = (
        order_details
        .filter(col("o_orderdate") > cutoff_date)
        .groupBy(
            col("l_partkey").alias("product_id"),
            "p_name",
            "p_mfgr",
            "p_brand",
            "p_type",
            "p_retailprice"
        )
        .agg(_sum("l_quantity").alias("total_sold"))
        .orderBy(col("total_sold").desc())
    )

    return result


@dlt.table(
    name="gold_product_sales_metrics",
    comment="Comprehensive product sales metrics including revenue",
    table_properties={
        "quality": "gold",
        "pipelines.autoOptimize.zOrderCols": "product_id"
    }
)
def gold_product_sales_metrics():
    """Calculate comprehensive product sales metrics."""
    order_details = dlt.read("silver_order_details")

    return (
        order_details
        .groupBy(
            col("l_partkey").alias("product_id"),
            "p_name",
            "p_mfgr",
            "p_brand",
            "p_type",
            "p_retailprice"
        )
        .agg(
            _sum("l_quantity").alias("total_quantity_sold"),
            _sum(col("l_extendedprice") * (1 - col("l_discount"))).alias("total_revenue"),
            _max("o_orderdate").alias("last_order_date")
        )
        .orderBy(col("total_revenue").desc())
    )
