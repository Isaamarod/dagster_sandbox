import dagster as dg
from dagster_quickstart.defs.resources import ImpalaResource

@dg.asset (group_name="ingested", kinds={"impala","python"})
def show_tables(database: ImpalaResource)-> dg.MaterializeResult:
    db_list = database.list_databases()
    print("Available databases:")
    print(db_list)

    return dg.MaterializeResult(
        metadata={
            'Number of records': dg.MetadataValue.str(db_list)
        }
    )