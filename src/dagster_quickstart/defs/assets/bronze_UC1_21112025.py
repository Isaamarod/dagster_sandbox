from dagster import asset
from dagster_quickstart.defs.resources import ImpalaResource

@asset
def show_tables(database: ImpalaResource)-> None:
    conn = database.get_connection()
    df = conn.sql("SHOW TABLES").execute()
    print(df)
    