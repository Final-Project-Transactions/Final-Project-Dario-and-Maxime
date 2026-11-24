"""
analytics.py - the calculations behind the Compare page.

The page calls compare(me, ids) and gets back one dict with everything it
shows: my spending per month, the mean and median spender, my percentile,
everybody's totals (for the histogram / ranking) and the split by category.

Rules this file follows:
- No SQL here. The only data source is db.get_monthly_totals(), which returns
  sums per user, month and category, never single transactions (privacy).
- Everything is in CHF per month, so users with 3 months of data can be
  compared with users who have 12 months.

How "per month" is calculated:
    For each user: total spending / number of months in which the user has
    at least one transaction.
    Example: 3 months with data, CHF 9,000 in total -> CHF 3,000 per month.
    Limitation: a month that is only partly covered (e.g. the current month,
    or the first month of a bank export that starts mid-month) counts as a
    full month and pulls the average down a bit.

Who is in the comparison:
    The ids passed in by the page, WITHOUT me (I am compared with the others,
    not with myself) and without users who have no transactions at all
    (they have no spending to compare, and counting them as CHF 0 would pull
    the mean and median down). n = number of people left.
"""

import pandas as pd

import db


# ----------------------------------------------------------------------
# Pure pandas helpers (no database, no Streamlit -> easy to test)
# ----------------------------------------------------------------------
def monthly_spending_by_category(totals):
    """Average spending per month for every user and category.

    totals: DataFrame with the columns user_id, month, category, total
            (the output of db.get_monthly_totals).

    Returns a DataFrame with one row per user (index = user_id) and one
    column per category. Values are CHF per month; a category the user
    never spent on is 0.
    """
    if totals.empty:
        return pd.DataFrame()

    totals = totals.copy()
    # Transactions without a category would be dropped by pivot_table,
    # so they are counted as "Other" (same as unknown merchants).
    totals["category"] = totals["category"].fillna("Other")

    # Sum per user and category over all months
    sums = totals.pivot_table(index="user_id", columns="category",
                              values="total", aggfunc="sum", fill_value=0)

    # Number of months in which each user has at least one transaction
    months = totals.groupby("user_id")["month"].nunique()

    # Divide every row (user) by that user's number of months
    per_month = sums.div(months, axis=0)
    per_month.columns.name = None
    return per_month


def percentile_of(value, others):
    """Share of the others (in %) who spend LESS than value.

    Matches the sentence on the page: "You spend more than X% of ...".
    People with exactly the same amount are not counted.
    """
    if len(others) == 0:
        return 0.0
    return float((others < value).mean() * 100)


def compare_from_totals(totals, me, ids):
    """All numbers for the Compare page, calculated from monthly totals.

    totals: output of db.get_monthly_totals for me AND the ids
    me:     my user id
    ids:    the user ids to compare with (may contain me; I am removed)
    """
    per_month = monthly_spending_by_category(totals)
    total_per_month = per_month.sum(axis=1) if not per_month.empty else pd.Series(dtype=float)

    # --- me ---
    has_my_data = me in per_month.index
    my_total = float(total_per_month[me]) if has_my_data else 0.0
    my_by_category = per_month.loc[me] if has_my_data else None

    # --- the others: without me and without users who have no data ---
    other_ids = [i for i in dict.fromkeys(int(i) for i in ids)
                 if i != me and i in per_month.index]
    others = per_month.loc[other_ids]
    group_totals = total_per_month.loc[other_ids].astype(float)
    group_totals.name = "CHF per month"

    result = {
        "my_total": my_total,
        "n": len(other_ids),
        "group_totals": group_totals,      # Series, index = user_id
        "my_by_category": None,
        "mean_by_category": None,
        "median_by_category": None,
    }

    if result["n"] == 0:
        # The page stops here ("Nobody to compare with yet.")
        result.update(mean=0.0, median=0.0, percentile=0.0)
        return result

    result["mean"] = float(group_totals.mean())
    result["median"] = float(group_totals.median())
    result["percentile"] = percentile_of(my_total, group_totals)

    # --- per category (only if I have spending to compare) ---
    if my_by_category is not None:
        # Same categories in all three Series, sorted by the others' mean
        mean_by_category = others.mean().sort_values(ascending=False)
        order = list(mean_by_category.index)
        order += [c for c in my_by_category.index if c not in order]
        result["mean_by_category"] = mean_by_category.reindex(order, fill_value=0.0)
        result["median_by_category"] = others.median().reindex(order, fill_value=0.0)
        result["my_by_category"] = my_by_category.reindex(order, fill_value=0.0)

    return result


# ----------------------------------------------------------------------
# Called by views/compare.py
# ----------------------------------------------------------------------
def compare(me, ids):
    """Compare user `me` with the users in `ids`.

    Returns a dict with:
        my_total            my spending, CHF per month (0 if I have no data)
        mean, median        of the others' spending per month
        percentile          % of the others who spend less than me
        n                   number of others with data
        group_totals        Series: others' CHF per month, index = user_id
        my_by_category      Series: my CHF per month per category (None if no data)
        mean_by_category    Series: others' mean per category
        median_by_category  Series: others' median per category
    """
    me = int(me)
    ids = [int(i) for i in ids]
    totals = db.get_monthly_totals(list(set(ids) | {me}))
    return compare_from_totals(totals, me, ids)
