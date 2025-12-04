import os
from typing import Optional

import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
from dotenv import load_dotenv


# ---------- Load environment ---------- #

load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID", "silver-ripple-355716")

BIGQUERY_TABLE_ALL = os.getenv(
    "BIGQUERY_TABLE_ALL",
    "silver-ripple-355716.stocks_idx.fact_fundamental_all"
)

BIGQUERY_TABLE_QUARTER = os.getenv(
    "BIGQUERY_TABLE_QUARTER",
    "silver-ripple-355716.stocks_idx.fact_fundamental_quarterly"
)

BIGQUERY_TABLE_CLASSIFICATION = os.getenv(
    "BIGQUERY_TABLE_CLASSIFICATION",
    "silver-ripple-355716.stocks_idx.stock_classification"
)


def get_bigquery_client(project_id: str) -> bigquery.Client:
    """
    Create and return a BigQuery client.
    """
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    print(f"[DEBUG] GOOGLE_APPLICATION_CREDENTIALS = {creds_path}")

    # Extra safety: check that the file exists
    if not creds_path:
        raise RuntimeError(
            "GOOGLE_APPLICATION_CREDENTIALS is not set. "
            "Check your .env file and load_dotenv()."
        )

    if not os.path.exists(creds_path):
        raise RuntimeError(
            f"Credentials file not found at path: {creds_path}. "
            "Use an absolute path in your .env."
        )

    return bigquery.Client(project=project_id)


def get_data(
    code: str,
    table: str,
    client: Optional[bigquery.Client] = None
) -> pd.DataFrame:
    """
    Generic helper:
    Fetch data for a given stock code from a specific BigQuery table
    with a simple WHERE code = @code filter.
    """
    if client is None:
        client = get_bigquery_client(PROJECT_ID)

    query = f"""
        SELECT *
        FROM `{table}`
        WHERE code = @code
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("code", "STRING", code)
        ]
    )

    try:
        query_job = client.query(query, job_config=job_config)
        df = query_job.to_dataframe()
        return df

    except GoogleCloudError as e:
        print(f"[ERROR] BigQuery error while fetching data for code '{code}' from {table}: {e}")
        return pd.DataFrame()

    except Exception as e:
        print(f"[ERROR] Unexpected error while fetching data for code '{code}' from {table}: {e}")
        return pd.DataFrame()


def get_all_same_subsector(
    code: str,
    client: Optional[bigquery.Client] = None
) -> pd.DataFrame:
    """
    Fetch data from BIGQUERY_TABLE_ALL for ALL tickers
    that are in the same sub_sector as the given code (ticker),
    based on the stock_classification table.
    """
    if client is None:
        client = get_bigquery_client(PROJECT_ID)

    query = f"""
        SELECT *
        FROM `{BIGQUERY_TABLE_ALL}`
        WHERE code IN (
          SELECT ticker
          FROM `{BIGQUERY_TABLE_CLASSIFICATION}`
          WHERE sub_sector = (
            SELECT sub_sector
            FROM `{BIGQUERY_TABLE_CLASSIFICATION}`
            WHERE ticker = @code
          )
        )
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("code", "STRING", code)
        ]
    )

    try:
        query_job = client.query(query, job_config=job_config)
        df = query_job.to_dataframe()
        return df

    except GoogleCloudError as e:
        print(f"[ERROR] BigQuery error while fetching ALL-table data for code '{code}': {e}")
        return pd.DataFrame()

    except Exception as e:
        print(f"[ERROR] Unexpected error while fetching ALL-table data for code '{code}': {e}")
        return pd.DataFrame()


def get_all_and_quarterly(
    code: str,
    client: Optional[bigquery.Client] = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Fetch data for a given stock code from BOTH:
    - BIGQUERY_TABLE_ALL (same-sub_sector logic)
    - BIGQUERY_TABLE_QUARTER (simple code filter)
    """
    if client is None:
        client = get_bigquery_client(PROJECT_ID)

    # NEW LOGIC: use the sub-sector based query for the ALL table
    df_all = get_all_same_subsector(code, client)

    # OLD LOGIC: still just filter on code for the QUARTER table
    df_quarter = get_data(code, BIGQUERY_TABLE_QUARTER, client)

    return df_all, df_quarter


def main():
    print(f"[DEBUG] PROJECT_ID                = {PROJECT_ID}")
    print(f"[DEBUG] BIGQUERY_TABLE_ALL        = {BIGQUERY_TABLE_ALL}")
    print(f"[DEBUG] BIGQUERY_TABLE_QUARTER    = {BIGQUERY_TABLE_QUARTER}")
    print(f"[DEBUG] BIGQUERY_TABLE_CLASSIFIER = {BIGQUERY_TABLE_CLASSIFICATION}")

    code = "UNVR"

    client = get_bigquery_client(PROJECT_ID)

    df_all, df_quarter = get_all_and_quarterly(code, client)

    print("\n[INFO] From BIGQUERY_TABLE_ALL (same sub_sector):")
    if df_all.empty:
        print(f"No data found in ALL table for sub_sector of code '{code}'.")
    else:
        print(df_all.head())

    print("\n[INFO] From BIGQUERY_TABLE_QUARTER (single code):")
    if df_quarter.empty:
        print(f"No data found in QUARTER table for code '{code}'.")
    else:
        print(df_quarter.head())


if __name__ == "__main__":
    main()
