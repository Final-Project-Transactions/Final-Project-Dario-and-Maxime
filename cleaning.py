"""
cleaning.py - turns a raw bank CSV into clean transactions.

Used by views/add_transactions.py. No Streamlit and no SQL in here, only
pandas, so the functions can be tested on their own.

Every bank exports differently, so the cleaning has to handle:
- dates like 01.11.2025, 01.11.25, 2025-11-01 or 01.11.2025 14:23
- amounts like -1'234.50, 1 234,50, CHF 12.30, 12.30- or 12,5
- expenses written as negative numbers (most banks) or as positive numbers
- empty rows, empty merchant fields and rows that are not transactions
"""

import csv
import datetime as dt
import io
import re
from collections import Counter

import pandas as pd

from categorize import categorize

def read_bank_csv(file, sep):
    """Read a bank CSV file -> (raw DataFrame, number of skipped info lines).

    Many banks (e.g. UBS) put info lines above the real table (account
    number, period, balance ...). We find the table ourselves: it is the
    block of lines that all have the same, most common number of columns.
    The first of those lines is the header.

    Also handles the encoding: Swiss bank exports are not always UTF-8.
    """
    data = file.getvalue() if hasattr(file, "getvalue") else file.read()
    for encoding in ["utf-8-sig", "cp1252", "latin-1"]:  # latin-1 never fails
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue

    lines = text.splitlines()
    # Number of columns per line (the csv module handles quotes correctly)
    widths = [len(row) for row in csv.reader(lines, delimiter=sep)]
    table_widths = [w for w in widths if w >= 2]
    if not table_widths:
        raise ValueError("No table found. Is the separator right?")
    width = Counter(table_widths).most_common(1)[0][0]
    header_line = widths.index(width)

    raw = pd.read_csv(
        io.StringIO(text), sep=sep, skiprows=header_line,
        on_bad_lines="skip",          # e.g. a total line at the end
        dtype=str,                    # keep amounts as text, we clean them ourselves
    )
    raw = raw.dropna(axis=1, how="all")  # empty columns (trailing ";")
    raw.columns = [str(c).strip() for c in raw.columns]
    return raw, header_line


# Date formats we try, in this order (Swiss formats first: day before month)
DATE_FORMATS = ["%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]


def parse_dates(series):
    """Text -> date (without time). Values that can't be read become NaT."""
    # Keep only the date part: "01.11.2025 14:23" -> "01.11.2025",
    # "2025-11-01T14:23:00" -> "2025-11-01"
    text = series.astype(str).str.strip().str.split(r"[ T]", n=1, regex=True).str[0]

    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    for fmt in DATE_FORMATS:
        missing = result.isna()
        if not missing.any():
            break
        # Fill only the rows that are still empty with this format
        result[missing] = pd.to_datetime(text[missing], format=fmt, errors="coerce")
    return result


def parse_amount(value):
    """One amount as text -> float, or None if it isn't a number.

    Examples: "-1'234.50" -> -1234.5, "1 234,50" -> 1234.5,
    "CHF 12.30" -> 12.3, "12.30-" -> -12.3
    """
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):  # pandas already read it as a number
        return float(value)

    text = str(value).strip().upper().replace("CHF", "")
    # Remove thousands separators: apostrophes and all kinds of spaces
    text = re.sub(r"['’\s  ]", "", text)

    # Minus at the end ("12.30-") is used by some banks
    if text.endswith("-"):
        text = "-" + text[:-1]

    # Decimal separator: if both "." and "," appear, the last one is the decimal
    if "." in text and "," in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")  # 1.234,50
        else:
            text = text.replace(",", "")                    # 1,234.50
    elif "," in text:
        # Only a comma: decimal if 1-2 digits follow ("12,5"), else thousands
        if re.search(r",\d{1,2}$", text):
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")

    try:
        return float(text)
    except ValueError:
        return None


def guess_expenses_negative(raw, col_amount):
    """Guess whether expenses are the negative numbers in this file.

    A bank statement has many more expenses than incoming payments, so the
    sign that appears more often is taken as "expense". The page lets the
    user correct the guess.
    """
    amounts = raw[col_amount].map(parse_amount).dropna()
    return bool((amounts < 0).sum() >= (amounts > 0).sum())


def clean_bank_csv(raw, col_date, col_merchant, col_amount, expenses_negative=True):
    """Raw CSV table -> (clean DataFrame, report dict).

    The clean DataFrame has exactly the columns date, merchant, amount,
    category, no empty values, and amount is always positive (CHF).

    expenses_negative=True: negative amounts are expenses, positive ones are
    income or refunds and are left out. False: all positive amounts are
    expenses, negative ones are left out.

    The report counts how many rows were dropped and why, so the page can
    tell the user.
    """
    df = pd.DataFrame({
        "date": parse_dates(raw[col_date]),
        "merchant": raw[col_merchant],
        "amount": raw[col_amount].map(parse_amount).astype("float64"),
    })
    n_start = len(df)

    # 1. Rows without a readable date are not transactions (empty lines,
    #    totals ...). Rows with a date but no amount in this column are
    #    usually income, when the bank has separate debit/credit columns (UBS).
    no_date = df["date"].isna()
    no_amount = ~no_date & df["amount"].isna()
    n_unreadable = int(no_date.sum())
    n_no_amount = int(no_amount.sum())
    df = df[~no_date & ~no_amount]

    # 2. Keep only expenses and make them positive
    if expenses_negative:
        is_expense = df["amount"] < 0
    else:
        is_expense = df["amount"] > 0
    n_income = int((~is_expense & (df["amount"] != 0)).sum())
    n_zero = int((df["amount"] == 0).sum())
    df = df[is_expense].copy()
    df["amount"] = df["amount"].abs().round(2)

    # 3. No future dates (a typo or a planned payment, not spent yet)
    future = df["date"].dt.date > dt.date.today()
    n_future = int(future.sum())
    df = df[~future]

    # 4. Merchant: clean text, "Unknown" if empty.
    #    Banks add details after a ";" (UBS: "Coop-1098 ZH;8037 Zürich",
    #    "MCDONALDS ZUERICH; Zahlung UBS TWINT"), we keep the part before it.
    merchant = df["merchant"].astype("string").str.split(";").str[0]
    merchant = merchant.str.strip(" ,")  # UBS TWINT: ", PAPI" -> "PAPI"
    merchant = merchant.str.replace(r"\s+", " ", regex=True)  # double spaces
    df["merchant"] = merchant.replace("", pd.NA).fillna("Unknown").astype(str)

    # 5. Date without time, category from the keyword rules
    df["date"] = df["date"].dt.date
    df["category"] = df["merchant"].map(categorize)

    df = df[["date", "merchant", "amount", "category"]].reset_index(drop=True)

    report = {
        "rows_in_file": n_start,
        "kept": len(df),
        "unreadable": n_unreadable,
        "no_amount": n_no_amount,
        "income_or_refund": n_income,
        "zero": n_zero,
        "future": n_future,
    }
    return df, report
