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

import datetime as dt
import re

import pandas as pd

from categorize import categorize

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

    # 1. Rows without a readable date or amount are not transactions
    #    (empty lines, totals, "Saldo" lines ...)
    bad = df["date"].isna() | df["amount"].isna()
    n_unreadable = int(bad.sum())
    df = df[~bad]

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

    # 4. Merchant: clean text, "Unknown" if empty
    merchant = df["merchant"].astype("string").str.strip()
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
        "income_or_refund": n_income,
        "zero": n_zero,
        "future": n_future,
    }
    return df, report
