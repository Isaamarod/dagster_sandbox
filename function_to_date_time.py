from typing import Union
import ibis


def to_date_time(
    column: ibis.expr.types.StringValue, only_date: bool = True
) -> Union[ibis.expr.types.DateValue, ibis.expr.types.TimestampValue]:
    """
    Converts an Ibis string column to Date or Timestamp format with strict validation.

    This function performs a guarded conversion of temporal strings. It validates that
    input data conforms to ISO standards and prevents data loss or "hallucinated"
    time components.

    Validation Logic:
    - If `only_date=True`: Accepts both 'YYYY-MM-DD' and 'YYYY-MM-DD HH:MM:SS'.
      The time component is truncated during conversion. Note that time values are
      not strictly validated for correctness (e.g., invalid times like '55:10:22'
      will be accepted but ignored).
    - If `only_date=False`: Strictly requires 'YYYY-MM-DD HH:MM:SS'. If the column
      only contains dates, an error is raised to prevent inferring null/zeroed times
      without explicit user consent.

    Note:
        This function calls `.execute()` to perform data quality checks. This will
        trigger a query to the backend (e.g., Impala).

        Midnight timestamps ('00:00:00') might be hidden in console output by Pandas.
        This is purely visual; check .schema() for type confirmation.

    Args:
        column: An Ibis string expression containing temporal data.
        only_date: If True, returns a DateValue. If False, returns a TimestampValue.
            Defaults to True.

    Returns:
        The casted Ibis expression (DateValue or TimestampValue).

    Raises:
        TypeError: If `column` is not an Ibis StringValue.
        ValueError: If invalid formats are detected, or if timestamp precision is
            requested for a column that only contains date strings.
    """
    # Validate the input column type
    if not isinstance(column, ibis.expr.types.StringValue):
        raise TypeError(
            "Input must be a string column (Ibis StringValue) containing temporal data."
        )

    # Regex pattern definition
    date_pattern = r"^\d{4}-\d{2}-\d{2}$"  # ISO date format: YYYY-MM-DD
    datetime_pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"  # ISO datetime format: YYYY-MM-DD HH:MM:SS
    time_present_pattern = r"\d{1,2}:\d{1,2}"  # Check for time presence (HH:MM)

    # Analyze the column to determine if it contains any time information
    # Note: .execute() triggers a query to the backend
    has_time_records = column.re_search(time_present_pattern).any().execute()

    # ERROR CASE: User asks for timestamps but the column contains only dates
    if not only_date and not has_time_records:
        raise ValueError(
            "Timestamp precision was requested (only_date=False), but the column only contains date-formatted strings. "
            "The program cannot infer time information. Please set only_date=True or "
            "manually append a default time string (e.g., ' 00:00:00') to the column before conversion."
        )

    # Identify invalid records
    if only_date:
        is_valid = column.re_search(date_pattern) | column.re_search(datetime_pattern)
        expected_format_desc = "ISO date (YYYY-MM-DD) or datetime (YYYY-MM-DD HH:MM:SS)"
    else:
        is_valid = column.re_search(datetime_pattern)
        expected_format_desc = "ISO datetime (YYYY-MM-DD HH:MM:SS)"

    # Check for invalid records
    invalid_count = (~is_valid).sum().execute()

    if invalid_count > 0:
        # Percentage of invalid records
        total_count = column.count().execute()
        percentage = (invalid_count / total_count) * 100

        # Get some examples of invalid records
        invalid_column_table = (
            column.as_table().filter(~is_valid).dropna().limit(5).execute()
        )
        examples = invalid_column_table.iloc[:, 0].tolist()

        error_msg = (
            f"\n{'!'*40}\n"
            f"INVALID FORMAT DETECTED\n"
            f"{'-'*40}\n"
            f"Expected format: {expected_format_desc}\n"
            f"Invalid records: {invalid_count:,}\n"
            f"Error percentage: {percentage:.2f}%\n"
            f"Sample of invalid values: {examples}\n"
            f"{'!'*40}"
        )

        raise ValueError(error_msg)

    # Perform the final conversion
    return column.cast("date") if only_date else column.cast("timestamp")
