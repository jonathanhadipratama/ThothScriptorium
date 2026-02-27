# src/data_extraction.py
import os
from typing import Optional, Any, Dict, Tuple

import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError

# ---------------------------------------------------------------------
# Config (read env vars; load_dotenv() should ideally be called
# in your Streamlit entry point, not here)
# ---------------------------------------------------------------------

PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID", "silver-ripple-355716")
BQ_LOCATION = os.getenv("BIGQUERY_LOCATION")  # optional; OK if None

SECTOR_FLOW_TABLE = os.getenv(
    "BIGQUERY_SECTOR_FLOW_TABLE",
    "silver-ripple-355716.adl.sector_flow_recent",
)

STOCK_FLOW_TABLE = os.getenv(
    "BIGQUERY_STOCK_FLOW_TABLE",
    "silver-ripple-355716.adl.stock_flow_recent",
)

SECTOR_RSI_TABLE = os.getenv(
    "BIGQUERY_SECTOR_RSI_TABLE",
    "silver-ripple-355716.adl.sector_rsi_recent",
)

SCREENER_MINERVINI_TABLE = os.getenv(
    "BIGQUERY_SECTOR_RSI_TABLE",
    "silver-ripple-355716.adl.screener_minervini_recent",
)

# (Your existing tables can stay here too if you still use them)
BIGQUERY_TABLE_ALL = os.getenv(
    "BIGQUERY_TABLE_ALL",
    "silver-ripple-355716.stocks_idx.fact_fundamental_all",
)
BIGQUERY_TABLE_QUARTER = os.getenv(
    "BIGQUERY_TABLE_QUARTER",
    "silver-ripple-355716.stocks_idx.fact_fundamental_quarterly",
)
BIGQUERY_TABLE_CLASSIFICATION = os.getenv(
    "BIGQUERY_TABLE_CLASSIFICATION",
    "silver-ripple-355716.stocks_idx.stock_classification",
)


# ---------------------------------------------------------------------
# Client + generic query runner
# ---------------------------------------------------------------------

def get_bigquery_client(project_id: str = PROJECT_ID) -> bigquery.Client:
    """
    Create and return a BigQuery client using ADC.

    - Locally, GOOGLE_APPLICATION_CREDENTIALS may point to a JSON key file.
    - On GCP (Cloud Run/GCE/etc.), it often uses the attached service account.
    """
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    # Only validate if explicitly set (so GCP runtime SA still works)
    if creds_path and not os.path.exists(creds_path):
        raise RuntimeError(
            f"Credentials file not found at path: {creds_path}. "
            "Use an absolute path in your .env."
        )

    return bigquery.Client(project=project_id)


def run_query(
    query: str,
    *,
    params: Optional[Dict[str, Tuple[str, Any]]] = None,
    client: Optional[bigquery.Client] = None,
) -> pd.DataFrame:
    """
    Run a BigQuery SQL query and return a pandas DataFrame.

    params format:
      {"code": ("STRING", "UNVR"), "min_ratio": ("FLOAT64", 0.3)}
    """
    client = client or get_bigquery_client()

    job_config = bigquery.QueryJobConfig()
    if params:
        job_config.query_parameters = [
            bigquery.ScalarQueryParameter(name, typ, val)
            for name, (typ, val) in params.items()
        ]

    try:
        query_job = client.query(query, job_config=job_config, location=BQ_LOCATION)
        return query_job.result().to_dataframe(create_bqstorage_client=True)

    except GoogleCloudError as e:
        print(f"[ERROR] BigQuery error: {e}")
        return pd.DataFrame()

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return pd.DataFrame()


# ---------------------------------------------------------------------
# Foreign Flow extractors (your new ones)
# ---------------------------------------------------------------------

def get_sector_flow(client: Optional[bigquery.Client] = None) -> pd.DataFrame:
    """
    Fetch sector flow data from:
      silver-ripple-355716.adl.sector_agg
    """
    query = f"""
        SELECT *
        FROM `{SECTOR_FLOW_TABLE}`
    """
    return run_query(query, client=client)


def get_stock_flow(client: Optional[bigquery.Client] = None) -> pd.DataFrame:
    """
    Fetch stock flow data from:
      silver-ripple-355716.adl.stock_flow_recent
    """
    query = f"""
        SELECT *
        FROM `{STOCK_FLOW_TABLE}`
    """
    return run_query(query, client=client)

def get_sector_rsi(client: Optional[bigquery.Client] = None) -> pd.DataFrame:
    """
    Fetch sector RSI data from:
      silver-ripple-355716.adl.sector_rsi_recent
    """
    query = f"""
        SELECT *
        FROM `{SECTOR_RSI_TABLE}`
    """
    return run_query(query, client=client)

def get_screener_minervini(client: Optional[bigquery.Client] = None) -> pd.DataFrame:
    """
    Fetch sector RSI data from:
      silver-ripple-355716.adl.screener_minervini
    """
    query = f"""
        SELECT *
        FROM `{SCREENER_MINERVINI_TABLE}`
    """
    return run_query(query, client=client)


SECTOR_FLOW_7D_VS_30D_TABLE = os.getenv(
    "BIGQUERY_SECTOR_FLOW_7D_VS_30D_TABLE",
    "silver-ripple-355716.adl.v_sector_flow_7d_vs_30d",
)

STOCK_FLOW_7D_VS_30D_TABLE = os.getenv(
    "BIGQUERY_STOCK_FLOW_7D_VS_30D_TABLE",
    "silver-ripple-355716.adl.v_stock_flow_7d_vs_30d",
)


def get_sector_flow_7d_vs_30d(client: Optional[bigquery.Client] = None) -> pd.DataFrame:
    """
    Fetch sector flow 7d vs 30d comparison data from:
      silver-ripple-355716.adl.v_sector_flow_7d_vs_30d
    """
    query = f"""
        SELECT *
        FROM `{SECTOR_FLOW_7D_VS_30D_TABLE}`
    """
    return run_query(query, client=client)


def get_stock_flow_7d_vs_30d(client: Optional[bigquery.Client] = None) -> pd.DataFrame:
    """
    Fetch stock flow 7d vs 30d comparison data from:
      silver-ripple-355716.adl.v_stock_flow_7d_vs_30d
    """
    query = f"""
        SELECT *
        FROM `{STOCK_FLOW_7D_VS_30D_TABLE}`
    """
    return run_query(query, client=client)


# ---------------------------------------------------------------------
# Your existing fundamentals helpers (kept as-is, but using run_query)
# ---------------------------------------------------------------------

def get_data(code: str, table: str, client: Optional[bigquery.Client] = None) -> pd.DataFrame:
    query = f"""
        SELECT *
        FROM `{table}`
        WHERE code = @code
    """
    return run_query(query, params={"code": ("STRING", code)}, client=client)


def get_all_same_subsector(code: str, client: Optional[bigquery.Client] = None) -> pd.DataFrame:
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
    return run_query(query, params={"code": ("STRING", code)}, client=client)


def get_all_and_quarterly(code: str, client: Optional[bigquery.Client] = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    client = client or get_bigquery_client()
    df_all = get_all_same_subsector(code, client)
    df_quarter = get_data(code, BIGQUERY_TABLE_QUARTER, client)
    return df_all, df_quarter
