import ibis
import yaml
import json
from datetime import datetime
from pathlib import Path


def ibis_types_compatible(expected: str, actual: str) -> bool:
    """
    Determines if two Ibis data types are compatible by normalizing aliases
    and grouping related types (e.g., all integer widths or string variants).

    Args:
        expected (str): Target type name (e.g., 'int64').
        actual (str): Current type name (e.g., 'bigint').

    Returns:
        bool: True if types match or belong to the same logical group.

    Note:
        Exact compatibility sets:
        - String: {string, str, text, varchar, char}
        - Integer: {int, int8, int16, int32, int64, uint8, uint16, uint32, uint64, integer, tinyint, smallint, bigint}
        - Float/Decimal: {float, float16, float32, float64, double, decimal, numeric, halffloat}
        - Boolean: {bool, boolean}
        - Temporal: {timestamp, datetime, timestamp_tz}
    """
    # Define groups: Every alias in a set is considered equal
    groups = [
        {"string", "str", "text", "varchar", "char"},
        {
            "int",
            "int8",
            "int16",
            "int32",
            "int64",
            "uint8",
            "uint16",
            "uint32",
            "uint64",
            "integer",
            "tinyint",
            "smallint",
            "bigint",
        },
        {
            "float",
            "float16",
            "float32",
            "float64",
            "double",
            "decimal",
            "numeric",
            "halffloat",
        },
        {"bool", "boolean"},
        {"timestamp", "datetime", "timestamp_tz"},
    ]

    # Helper to get the base name: "decimal(18,2)" -> "decimal"
    def base(t: str) -> str:
        return t.lower().split("(")[0].split("<")[0].strip()

    t1, t2 = base(expected), base(actual)

    if t1 == t2:
        return True

    # Check if both types exist within the same group
    return any(t1 in g and t2 in g for g in groups)


def string_format_analysis(table: ibis.Table, col_name: str) -> dict:
    """
    This function analyzes the format of string values in a specified column of an Ibis table.
    It categorizes the values based on predefined regex patterns (e.g., date formats, numeric
    formats, text formats) and counts the occurrences of each format category. The function returns
    a dictionary with the format categories as keys and their corresponding counts as values.

    Args:
        table (ibis.Table): The Ibis table containing the column to analyze.
        col_name (str): The name of the column to analyze.

    Returns:
        dict: A dictionary where the keys are format categories (e.g., "iso_datetime",
        "decimal", "only_alpha") and the values are the counts of occurrences for each category.

    Note:
        The function uses a hierarchical approach to categorize the formats, starting with more specific
        patterns (e.g., ISO datetime) and moving to more general ones (e.g., alphanumeric). If a value
        matches multiple patterns, it will be categorized based on the first match in the hierarchy. Values
        that do not match any of the predefined patterns will be categorized as "mixed_or_other".

    Example format categories:
        - "iso_datetime_t": ISO datetime format with 'T' separator (e.g., "2023-10-01T12:00:00")
        - "iso_datetime_space": ISO datetime format with space separator (e.g., "2023-10-01 12:00:00")
        - "iso_date_only": ISO date format without time (e.g., "2023-10-01")
        - "slash_datetime": Datetime format with slashes (e.g., "10/01/2023 12:00:00")
        - "slash_date_only": Date format with slashes (e.g., "10/01/2023")
        - "time_only": Time format (e.g., "12:00:00")
        - "decimal_dot": Decimal number with dot as separator (e.g., "123.45")
        - "decimal_comma": Decimal number with comma as separator (e.g., "123,45")
        - "mixed_separators": Number containing both dots and commas as separators (e.g., "1.234,56" or "1,234.56")
        - "integer": Integer number (e.g., "123")
        - "only_alpha": Text containing only alphabetic characters (e.g., "Hello World") #TODO: Añadir . y , ?
        - "alphanumeric": Text containing both alphabetic and numeric characters (e.g., "Hello123") #TODO: Añadir . y , ?
        - "mixed_or_other": Values that do not fit into any of the above categories (e.g., "Hello 123Ç+^&*()")
    """

    # Get the column object
    column = table[col_name]

    # Regex patterns definitions (Hierarchy: more specific to more general)
    patterns = {
        # 1. Dates and timestamps (ISO: YYYY-MM-DD, with optional time component)
        "iso_datetime_t": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$",  # Using T: 2023-10-01T12:00:00
        "iso_datetime_space": r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?$",  # Using space: 2023-10-01 12:00:00
        "iso_date_only": r"^\d{4}-\d{2}-\d{2}$",  # Only date: 2023-10-01
        # 2. Dates and timestamps (Slash: MM/DD/YYYY, with optional time component)
        "slash_datetime": r"^\d{1,2}/\d{1,2}/\d{4} \d{2}:\d{2}:\d{2}$",  # Using slash with time: 10/01/2023 12:00:00
        "slash_date_only": r"^\d{1,2}/\d{1,2}/\d{4}$",  # Using slash only for date: 10/01/2023
        # 3. Times (HH:MM:SS)
        "time_only": r"^\d{2}:\d{2}:\d{2}$",  # Time only: 12:00:00
        # 4. Numeric formats
        "decimal_dot": r"^[+-]?\d+\.\d+$",  # 123.45
        "decimal_comma": r"^[+-]?\d+,\d+$",  # 123,45
        "mixed_separators": r"^[+-]?(\d+[\.]\d+[,]\d+|\d+[,]\d+[\.]\d+)[\d.,]*$",  # 1.234,56 or 1,234.56
        "integer": r"^[+-]?\d+$",  # 123
        # 5. Text
        "only_alpha": r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s\-_.,:;]+$",  # Includes accented characters and common text symbols
        "alphanumeric": r"^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\-_.,:;]+$",  # Include previous plus numbers
    }

    expr = ibis.ifelse(
        column.isnull(),
        "null",
        ibis.ifelse(
            column == "",
            "empty_string",
            ibis.ifelse(
                column.re_search(patterns["iso_datetime_t"]),
                "iso_datetime_t",
                ibis.ifelse(
                    column.re_search(patterns["iso_datetime_space"]),
                    "iso_datetime_space",
                    ibis.ifelse(
                        column.re_search(patterns["slash_datetime"]),
                        "slash_datetime",
                        ibis.ifelse(
                            column.re_search(patterns["iso_date_only"]),
                            "iso_date_only",
                            ibis.ifelse(
                                column.re_search(patterns["slash_date_only"]),
                                "slash_date_only",
                                ibis.ifelse(
                                    column.re_search(patterns["time_only"]),
                                    "time_only",
                                    ibis.ifelse(
                                        column.re_search(patterns["decimal_dot"]),
                                        "decimal_dot",
                                        ibis.ifelse(
                                            column.re_search(patterns["decimal_comma"]),
                                            "decimal_comma",
                                            ibis.ifelse(
                                                column.re_search(
                                                    patterns["mixed_separators"]
                                                ),
                                                "mixed_separators",
                                                ibis.ifelse(
                                                    column.re_search(
                                                        patterns["integer"]
                                                    ),
                                                    "integer",
                                                    ibis.ifelse(
                                                        column.re_search(
                                                            patterns["only_alpha"]
                                                        ),
                                                        "only_alpha",
                                                        ibis.ifelse(
                                                            column.re_search(
                                                                patterns["alphanumeric"]
                                                            ),
                                                            "alphanumeric",
                                                            "mixed_or_other",
                                                        ),
                                                    ),
                                                ),
                                            ),
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    working_table = table.mutate(format_category=expr)

    results = (
        working_table.group_by("format_category")
        .aggregate(total=working_table.count())
        .execute()
    )

    return dict(zip(results["format_category"], results["total"]))


def get_column_stats(
    table: ibis.Table,
    col_name: str,
    bad_null_values: list = None,
    sentinel_values: list = None,
) -> dict:
    """
    This function computes various statistics for a given column in an Ibis table based on its data type.
    It returns a dictionary containing the computed statistics for the specified column.

    Args:
        table (ibis.Table): The Ibis table containing the column to profile.
        col_name (str): The name of the column for which to compute statistics.
        bad_null_values (list, optional): A list of values that should be considered as "bad nulls" (e.g., empty strings, specific sentinel values).
        sentinel_values (list, optional): A list of values that should be considered as "sentinel values" (e.g., specific values that indicate missing data).

    Returns:
        dict: A dictionary containing the computed statistics for the specified column.
    """

    # Get the column object and its data type
    column = table[col_name]
    col_type = column.type()

    # Base table for aggregations
    working_table = table

    # Base metrics (common for all types)
    metrics = {
        "name": ibis.literal(col_name),
        "type": ibis.literal(str(col_type)),
        "null_count": column.isnull().sum(),
        "non_null_count": column.notnull().sum(),
    }

    # Bad Nulls analysis
    if bad_null_values:
        for val in bad_null_values:
            metrics[f"bn_{val}"] = (column == val).cast("int").sum()

    # Sentinel analysis
    if sentinel_values:
        for val in sentinel_values:
            metrics[f"sv_{val}"] = (column == val).cast("int").sum()

    # Logic for NUMERIC types
    if col_type.is_numeric():

        # To compute quartiles, we need to calculate the percentiles using a window function.
        window = ibis.window(order_by=column)
        working_table = table.mutate(_percentil=ibis.percent_rank().over(window))

        # Reference to the column and the percentile for easier use in the metrics dictionary
        col_ref = working_table[col_name]
        perc_ref = working_table["_percentil"]

        # Update the metrics dictionary with numeric-specific statistics
        q1 = ibis.ifelse(perc_ref >= 0.25, col_ref, ibis.null()).min()
        q3 = ibis.ifelse(perc_ref >= 0.75, col_ref, ibis.null()).min()

        metrics.update(
            {
                "mean": col_ref.mean(),
                "stddev": col_ref.std(),
                "min": col_ref.min(),
                "q1": q1,
                "median": ibis.ifelse(perc_ref >= 0.50, col_ref, ibis.null()).min(),
                "q3": q3,
                "max": col_ref.max(),
                "iqr": q3 - q1,
            }
        )

    # Logic for STRING types
    elif col_type.is_string():
        # To check for leading/trailing spaces.
        has_leading_trailing_spaces = column.re_search(r"^\s|\s$")
        has_consecutives_spaces = column.re_search(r"\s{2,}")

        # Update the metrics dictionary with string-specific statistics
        metrics.update(
            {
                "unique_count": column.nunique(),
                "length_min": column.length().min(),
                "length_mean": column.length().mean(),
                "length_max": column.length().max(),
                "length_stddev": column.length().std(),
                "rows_with_padding": has_leading_trailing_spaces.cast("int").sum(),
                "rows_with_consecutive_spaces": has_consecutives_spaces.cast(
                    "int"
                ).sum(),
            }
        )

    # Logic for BOOLEAN types
    elif col_type.is_boolean():
        metrics.update(
            {
                "true_count": column.sum(),
                "false_count": column.notnull().sum() - column.sum(),
            }
        )

    # Logic for TEMPORAL types
    elif col_type.is_temporal():
        metrics.update(
            {
                "min": column.min(),
                "max": column.max(),
                "range": column.max() - column.min(),
            }
        )

    # --- Execution of the aaggregation ---
    # We use working_table because if it's numeric, it needs the _percentil column
    results = working_table.aggregate(**metrics).execute().to_dict("records")[0]

    final_stats = {k: v for k, v in results.items() if not k.startswith(("bn_", "sv_"))}
    final_stats["bad_nulls_detail"] = {
        k.replace("bn_", ""): v for k, v in results.items() if k.startswith("bn_")
    }
    final_stats["sentinels_detail"] = {
        k.replace("sv_", ""): v for k, v in results.items() if k.startswith("sv_")
    }

    # Post-processing for string columns
    if col_type.is_string():
        # Most common values in the column
        final_stats["top5"] = column.topk(5).execute()

        # Format analysis for string columns
        final_stats["format_distribution"] = string_format_analysis(table, col_name)

    return final_stats


def get_repeated_rows_count(table: ibis.Table) -> int:
    """
    This function computes the number of repeated rows in an Ibis table by comparing the total row count
    with the count of distinct rows. It returns the number of repeated rows.

    Args:
        table (ibis.Table): The Ibis table for which to compute the number of repeated rows.

    Returns:
        int: The number of repeated rows in the table.

    Note:
        One row can be repeated multiple times, but it will only be counted once in the distinct count.
        The number of repeated rows is calculated as: repeated_rows = total_rows - distinct_rows
    """
    total_rows = table.count().execute()
    unique_rows = table.distinct().count().execute()
    repeated_rows = total_rows - unique_rows
    return repeated_rows


def get_duplicate_columns(table: ibis.Table) -> list:
    """
    This function identifies columns in an Ibis table that have identical content by comparing
    each pair of columns only once (i.e., comparing column A with B but not B with A). It first
    checks for type compatibility using the `ibis_types_compatible` function, and if the are
    compatible, it uses the `identical_to` method to check if the columns are identical at the
    data level. The function returns a list of tuples containing the names of the columns that
    are identical.

    Args:
        table (ibis.Table): The Ibis table for which to identify duplicate columns.

    Returns:
        list: A list of tuples, where each tuple contains the names of two columns that have
        identical content (e.g., [("column_a", "column_b"), ("column_c", "column_d")]).
    """

    # Get the list of columns in the table
    cols = table.columns
    num_cols = len(cols)
    duplicates = []

    # Compare each pair of columns only once (i < j) to avoid redundant comparisons
    for i in range(num_cols):
        for j in range(i + 1, num_cols):
            col_a = cols[i]
            col_b = cols[j]

            # Check type compatibility first to avoid unnecessary data comparisons
            type_a = str(table[col_a].type())
            type_b = str(table[col_b].type())

            if ibis_types_compatible(type_a, type_b):
                # Verify if the columns are identical at the data level
                # if the value is NULL in both columns, it will be considered identical for that row
                is_identical = table.aggregate(
                    match=table[col_a].identical_to(table[col_b]).all()
                ).execute()["match"][0]

                if is_identical:
                    duplicates.append((col_a, col_b))

    return duplicates


def print_profiling_report(
    profiling_results: dict, table: ibis.Table, contract: dict
) -> None:
    """
    This function takes the profiling results for each column and prints a formatted
    profiling report to the console. The report includes general information about the table
    (total rows and columns) as well as the computed statistics for each column.

    Args:
        profiling_results (dict): A dictionary containing the computed statistics for each column.
        table (ibis.Table): The Ibis table for which the profiling report is being generated.
        contract (dict): The contract information for the table.
    """

    # Get the table name safely
    table_name = table.get_name().split(".")[-1]

    # Print the profiling report header with the table name
    print(f" PROFILING REPORT FOR TABLE: {table_name} ".center(80, "="))

    # Print general info about the table
    t_stats = profiling_results.get("table_stats", {})
    print(f"Total Rows: {t_stats.get('total_rows', 'N/A')}")
    print(f"Total Columns: {t_stats.get('total_columns', 'N/A')}")
    print(f"Repeated Rows: {t_stats.get('repeated_rows', 'N/A')}")

    # Print duplicate columns if any
    dup_cols = t_stats.get("duplicate_columns", [])
    if dup_cols:
        formatted_dups = "\n  ".join([f"{a} & {b}" for a, b in dup_cols])
        print(f"Duplicate Columns:\n  {formatted_dups}")
        print(f"⚠️ Warning: Detected {len(dup_cols)} pair(s) of columns with identical data.")  
    else:
        print("Duplicate Columns: None")

    # Loop through the profiling results and print the statistics for each column
    for col_name, stats in profiling_results.get("columns_stats", {}).items():

        # Get column contract information safely
        col_contract = contract.get("columns", {}).get(col_name, {})
        type_in_contract = col_contract.get("type", "N/A")
        nullable_in_contract = col_contract.get("nullable", "N/A")

        # Print the statistics for the current column
        print(f"\nColumn: {col_name}")
        for stat_name, stat_value in stats.items():

            # Custom formatting for specific statistics
            if stat_name == "top5":
                print(f"  {stat_name}:\n {stat_value}")

            elif stat_name in ["bad_nulls_detail", "sentinels_detail"]:
                print(f"  {stat_name}:")
                if isinstance(stat_value, dict) and stat_value:
                    for key, count in stat_value.items():
                        if count > 0:
                            print(f"    '{key}': {count}")
                
            elif stat_name == "type":
                print(f"  {stat_name}: {stat_value} (Contract: {type_in_contract})")
                if type_in_contract != "N/A" and not ibis_types_compatible(
                    type_in_contract, stat_value
                ):
                    print(
                        "⚠️ Warning: Data type in contract does not match the actual data type."
                    )
            elif stat_name == "null_count":
                print(
                    f"  {stat_name}: {stat_value} (Contract nullable: {nullable_in_contract})"
                )
                if nullable_in_contract != "N/A":
                    if stat_value > 0 and nullable_in_contract is False:
                        print(
                            "⚠️ Warning: Column contains null values but contract specifies it as non-nullable."
                        )
            elif stat_name == "format_distribution":
                print(f"  {stat_name}:")
                for format_category, count in stat_value.items():
                    print(f"    {format_category}: {count}")
                # String Format warnings
                if len(stat_value) > 1:
                    print("⚠️ Warning: Multiple data formats detected in your column.")
                if "decimal_comma" in stat_value:
                    print(
                        "⚠️ Warning: Some decimal numbers use a comma (,) as a separator. This may cause errors during data casting."
                    )
                if any(k in stat_value for k in ["slash_datetime", "slash_date_only"]):
                    print(
                        "⚠️ Warning: Non-ISO date formats detected. Please ensure all dates follow the YYYY-MM-DD HH:MM:SS format for correct casting."
                    )
            else:
                print(f"  {stat_name}: {stat_value}")


def ibis_profiling_report(
    table: ibis.Table, contract: dict, output_dir: Path, profiling_number: int
) -> None:
    """
    Generate a profiling report for an Ibis table using the engine's capabilities.
    This function will print out the basic statistics for each column (it depends on
    the type of columns).

    Args:
        table (ibis.Table): The Ibis table to profile.
        contract (dict): The contract information for the table loaded from the YAML file.
        output_dir (Path): Path to the directory where the profiling report JSON files will be saved.
        profiling_number (int): An identifier for the profiling run, used for naming output files if needed.
            After loading first time (1), after first transformation (2), after second transformation (3), etc.
    """
    # Create a dictionary with table stats
    table_global_stats = {
        "total_rows": table.count().execute(),
        "total_columns": len(table.columns),
        "repeated_rows": get_repeated_rows_count(table),
        "duplicate_columns": get_duplicate_columns(table),
    }

    # Initialize a dictionary to hold the profiling results for each column
    columns_stats = {}

    # Loop through each column in the table and compute statistics
    for col_name in table.columns:
        # Get the list of bad null values
        bad_nulls_list = (
            contract.get("columns", {}).get(col_name, {}).get("bad_nulls", [])
        )

        # Get the list of sentinel values
        sentinel_values_list = (
            contract.get("columns", {}).get(col_name, {}).get("sentinel_values", [])
        )

        columns_stats[col_name] = get_column_stats(
            table, col_name, bad_nulls_list, sentinel_values_list
        )

    # Combine both global table stats and column stats
    profiling_results = {
        "table_stats": table_global_stats,
        "columns_stats": columns_stats,
    }    

    # Print the profiling report
    print_profiling_report(profiling_results, table, contract)

    # Reformat top5 for saving
    for col_name, stats in profiling_results["columns_stats"].items():
        if "top5" in stats:
            df_top5 = stats["top5"]
            # Create the dictionary
            stats["top5"] = dict(zip(df_top5.iloc[:, 0], df_top5.iloc[:, 1]))

    # Save the table profiling results to a JSON file
    table_name = table.get_name().split(".")[-1]
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = (
        output_dir
        / f"profiling_report_{profiling_number}_{table_name}_{current_time}.json"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profiling_results, f, indent=4, default=str, ensure_ascii=False)


def table_list_profiling_reports(
    table_names: list,
    ibis_client: ibis.BaseBackend,
    database_name: str,
    contract_dir: Path,
    output_dir: Path,
    profiling_number: int,
) -> None:
    """
    This function generates profiling reports for a list of tables in an Ibis-supported database.
    It takes a list of table names, an Ibis client for connecting to the database, and optional
    dictionaries for "bad null" values and "sentinel" values. The function retrieves each table
    using the Ibis client, generates a profiling report for each table using the
    `ibis_profiling_report` function, and prints the reports to the console.

    Args:
        table_names (list): A list of table names to profile.
        ibis_client (ibis.Client): The Ibis client to use for connecting to the database.
            database_name (str): The name of the database containing the tables.
        contract_dir (Path): Path to the directory containing the YAML contract files for
            each table. Each contract file should be named as "{table_name}.yaml".
        output_dir (Path): Path to the directory where the profiling report JSON files will be saved.
        profiling_number (int): An identifier for the profiling run, used for naming output files if needed.
            After loading first time (1), after first transformation (2), after second transformation (3), etc.

    Example usage:
        tables = ["table1", "table2", "table3"]
        ibis_client = ibis.connect("your_database_connection_string")
        database_name = "your_database_name"
        contract_dir = Path("path/to/contract/files")
        output_dir = Path("path/to/output/files")
        profiling_number = 1

        table_list_profiling_reports(tables, ibis_client, database_name, contract_dir, output_dir, profiling_number)
    """

    # Loop through each table name
    for table_name in table_names:

        # Get the Ibis table object
        table = ibis_client.table(table_name, database=database_name)

        # Get the contract for the current table
        try:
            with open(contract_dir / f"{table_name}.yaml", "r") as file:
                contract = yaml.safe_load(file)
        except FileNotFoundError:
            print(
                f"⚠️ Warning: Contract file for table '{table_name}' not found in '{contract_dir}'."
            )
            contract = {}

        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate the profiling report for the current table
        ibis_profiling_report(table, contract, output_dir, profiling_number)
