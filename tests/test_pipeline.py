"""Tests for the DLT pipeline transformations."""

import pytest
from datetime import datetime, timedelta
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DateType, DecimalType
from chispa.dataframe_comparer import assert_df_equality


@pytest.fixture(scope="session")
def spark():
    """Create a Spark session for testing."""
    return (
        SparkSession.builder
        .appName("test_pipeline")
        .master("local[2]")
        .getOrCreate()
    )


def test_order_lineitem_join(spark):
    """Test joining orders and lineitems."""
    # Create sample orders data
    orders_schema = StructType([
        StructField("o_orderkey", IntegerType(), False),
        StructField("o_orderdate", DateType(), False),
    ])

    orders_data = [
        (1, datetime(2024, 1, 1).date()),
        (2, datetime(2024, 1, 2).date()),
    ]

    orders_df = spark.createDataFrame(orders_data, orders_schema)

    # Create sample lineitem data
    lineitem_schema = StructType([
        StructField("l_orderkey", IntegerType(), False),
        StructField("l_partkey", IntegerType(), False),
        StructField("l_quantity", DecimalType(15, 2), False),
    ])

    lineitem_data = [
        (1, 101, 5.0),
        (1, 102, 3.0),
        (2, 101, 2.0),
    ]

    lineitem_df = spark.createDataFrame(lineitem_data, lineitem_schema)

    # Perform join
    result = orders_df.join(lineitem_df, orders_df.o_orderkey == lineitem_df.l_orderkey)

    # Assertions
    assert result.count() == 3
    assert "o_orderkey" in result.columns
    assert "l_partkey" in result.columns


def test_aggregation_logic(spark):
    """Test product sales aggregation logic."""
    # Create sample data
    schema = StructType([
        StructField("l_partkey", IntegerType(), False),
        StructField("l_quantity", DecimalType(15, 2), False),
        StructField("p_name", StringType(), False),
    ])

    data = [
        (101, 5.0, "Product A"),
        (101, 3.0, "Product A"),
        (102, 2.0, "Product B"),
    ]

    df = spark.createDataFrame(data, schema)

    # Perform aggregation
    result = (
        df.groupBy("l_partkey", "p_name")
        .agg({"l_quantity": "sum"})
        .withColumnRenamed("sum(l_quantity)", "total_sold")
        .orderBy("total_sold", ascending=False)
    )

    # Assertions
    assert result.count() == 2
    first_row = result.first()
    assert first_row["l_partkey"] == 101
    assert float(first_row["total_sold"]) == 8.0


def test_date_filtering(spark):
    """Test filtering by date range."""
    schema = StructType([
        StructField("o_orderdate", DateType(), False),
        StructField("quantity", IntegerType(), False),
    ])

    max_date = datetime(2024, 3, 1).date()
    cutoff_date = max_date - timedelta(days=30)

    data = [
        (datetime(2024, 2, 15).date(), 5),  # Within 30 days
        (datetime(2024, 2, 28).date(), 3),  # Within 30 days
        (datetime(2024, 1, 15).date(), 2),  # Outside 30 days
    ]

    df = spark.createDataFrame(data, schema)

    # Filter data
    result = df.filter(df.o_orderdate > cutoff_date)

    # Assertions
    assert result.count() == 2
    for row in result.collect():
        assert row["o_orderdate"] > cutoff_date


def test_data_quality_checks(spark):
    """Test data quality expectations."""
    schema = StructType([
        StructField("o_orderkey", IntegerType(), True),
        StructField("l_partkey", IntegerType(), True),
        StructField("l_quantity", DecimalType(15, 2), True),
    ])

    data = [
        (1, 101, 5.0),  # Valid
        (None, 102, 3.0),  # Invalid: null orderkey
        (3, None, 2.0),  # Invalid: null partkey
        (4, 104, -1.0),  # Invalid: negative quantity
        (5, 105, 0.0),  # Invalid: zero quantity
    ]

    df = spark.createDataFrame(data, schema)

    # Apply quality checks (drop invalid rows)
    clean_df = df.filter(
        (df.o_orderkey.isNotNull()) &
        (df.l_partkey.isNotNull()) &
        (df.l_quantity > 0)
    )

    # Assertions
    assert clean_df.count() == 1  # Only one valid row
