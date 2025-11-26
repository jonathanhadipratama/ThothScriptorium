import os
from typing import Optional

import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
from dotenv import load_dotenv


# ---------- Load environment ---------- #

# Load variables from .env in the current working directory
load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID", "silver-ripple-355716")
DATASET_TABLE = os.getenv(
    "BIGQUERY_TABLE",
    "silver-ripple-355716.stocks_idx.fact_fundamental_quarterly"
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


def get_data(code: str, client: Optional[bigquery.Client] = None) -> pd.DataFrame:
    """
    Fetch quarterly fundamental data for a given stock code from BigQuery.
    """
    if client is None:
        client = get_bigquery_client(PROJECT_ID)

    query = f"""
        SELECT *
        FROM `{DATASET_TABLE}`
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
        print(f"[ERROR] BigQuery error while fetching data for code '{code}': {e}")
        return pd.DataFrame()

    except Exception as e:
        print(f"[ERROR] Unexpected error while fetching data for code '{code}': {e}")
        return pd.DataFrame()


def main():
    # Just to be sure: show important env vars
    print(f"[DEBUG] PROJECT_ID   = {PROJECT_ID}")
    print(f"[DEBUG] DATASET_TABLE = {DATASET_TABLE}")

    code = "UNVR"
    df = get_data(code)

    if df.empty:
        print(f"No data found for code '{code}'.")
    else:
        print(df.head())


if __name__ == "__main__":
    main()
