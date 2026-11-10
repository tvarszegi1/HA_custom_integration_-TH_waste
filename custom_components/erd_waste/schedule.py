"""Waste collection schedule calculation logic for Érd and surrounding areas."""
import calendar
from datetime import date, timedelta
import logging
import re

_LOGGER = logging.getLogger(__name__)

DAYS_HU = {
    "hétfő": 0, "hetfo": 0,
    "kedd": 1,
    "szerda": 2,
    "csütörtök": 3, "csutortok": 3,
    "péntek": 4, "pentek": 4,
    "szombat": 5,
    "vasárnap": 6, "vasarnap": 6,
}

# Érd route code mapping: code -> (target_weekday: 0=Mon..4=Fri, target_iso_parity: 0=Even, 1=Odd)
ERD_SZELEKTIV2_MAP = {
    120: (0, 0),   # Monday, Even ISO weeks
    219: (1, 0),   # Tuesday, Even ISO weeks
    318: (2, 0),   # Wednesday, Even ISO weeks
    417: (3, 1),   # Thursday, Odd ISO weeks
    516: (4, 1),   # Friday, Odd ISO weeks
    615: (0, 1),   # Monday, Odd ISO weeks
    714: (1, 1),   # Tuesday, Odd ISO weeks
    813: (2, 1),   # Wednesday, Odd ISO weeks
    912: (3, 0),   # Thursday, Even ISO weeks
    1011: (4, 0),  # Friday, Even ISO weeks
}

# Fallback string mappings to route codes in Érd
ERD_SZELEKTIV_STR_MAP = {
    "1_1_hetfo": 120, "4_20_pentek": 120,
    "1_2_kedd": 219, "4_19_csutortok": 219,
    "1_3_szerda": 318, "4_18_szerda": 318,
    "1_4_csutortok": 417, "4_17_kedd": 417,
    "1_5_pentek": 516, "4_16_hetfo": 516,
    "2_6_hetfo": 615, "3_15_pentek": 615,
    "2_7_kedd": 714, "3_14_csutortok": 714,
    "2_8_szerda": 813, "3_13_szerda": 813,
    "2_9_csutortok": 912, "3_12_kedd": 912,
    "2_10_pentek": 1011, "3_11_hetfo": 1011,
}


def get_nth_weekday_of_month(year: int, month: int, weekday_idx: int, n: int) -> date | None:
    """Return the date of the nth weekday (1-indexed) in a given month."""
    cal = calendar.monthcalendar(year, month)
    dates = [week[weekday_idx] for week in cal if week[weekday_idx] != 0]
    if 1 <= n <= len(dates):
        return date(year, month, dates[n - 1])
    return None


def get_feature_street_name(props: dict) -> str:
    """Extract street name from GeoJSON feature properties with fallbacks for all cities."""
    return (
        props.get("name")
        or props.get("teljesnev")
        or props.get("lista")
        or props.get("kommunalisnev")
        or ""
    ).strip()


def calculate_schedule(
    city: str,
    props: dict,
    start_date: date,
    days_ahead: int = 150,
) -> dict[str, list[date]]:
    """Calculate upcoming collection dates for all waste types from street properties."""
    schedule: dict[str, list[date]] = {}
    end_date = start_date + timedelta(days=days_ahead)

    # 1. KOMMUNÁLIS (Vegetable / general waste: weekly on assigned day)
    komm_val = props.get("kommunalis")
    if komm_val:
        wday = DAYS_HU.get(str(komm_val).strip().lower())
        if wday is not None:
            komm_dates = []
            curr = start_date
            while curr <= end_date:
                if curr.weekday() == wday:
                    komm_dates.append(curr)
                curr += timedelta(days=1)
            schedule["kommunalis"] = sorted(komm_dates)

    # 2. SZELEKTÍV (Recyclable waste)
    szel_dates = []
    if city == "Érd":
        sz2 = props.get("szelektiv2")
        code = int(sz2) if sz2 and str(sz2).isdigit() else None
        if not code:
            sz_str = str(props.get("szelektiv", "")).strip().lower()
            code = ERD_SZELEKTIV_STR_MAP.get(sz_str)

        if code in ERD_SZELEKTIV2_MAP:
            target_wday, target_parity = ERD_SZELEKTIV2_MAP[code]
            curr = start_date
            while curr <= end_date:
                if curr.weekday() == target_wday and (curr.isocalendar()[1] % 2 == target_parity):
                    szel_dates.append(curr)
                curr += timedelta(days=1)
    elif city in ("Diósd", "Tárnok", "Ráckeresztúr"):
        # Diósd: Saturday on even ISO weeks; Tárnok & Ráckeresztúr: Monday on even ISO weeks
        target_wday = 5 if city == "Diósd" else 0
        curr = start_date
        while curr <= end_date:
            if curr.weekday() == target_wday and (curr.isocalendar()[1] % 2 == 0):
                szel_dates.append(curr)
            curr += timedelta(days=1)
    elif city == "Sóskút":
        # 2nd and 4th Wednesday of each month
        curr = start_date
        while curr <= end_date:
            if curr.weekday() == 2:
                d2 = get_nth_weekday_of_month(curr.year, curr.month, 2, 2)
                d4 = get_nth_weekday_of_month(curr.year, curr.month, 2, 4)
                if curr in (d2, d4):
                    szel_dates.append(curr)
            curr += timedelta(days=1)

    if szel_dates:
        schedule["szelektiv"] = sorted(szel_dates)

    # 3. ZÖLDHULLADÉK (Green waste)
    zold_dates = []
    if city == "Érd":
        z2 = str(props.get("zoldhulladek2", "")).strip()
        z1 = str(props.get("zoldhulladek", "")).strip()
        is_13 = (z2 == "13" or z1 in ("1", "3"))

        curr = start_date
        while curr <= end_date:
            if curr.weekday() == 5:  # Saturday
                m = curr.month
                if 3 <= m <= 11:
                    # March to November: bi-weekly (13 = odd ISO weeks, 24 = even ISO weeks)
                    target_parity = 1 if is_13 else 0
                    if curr.isocalendar()[1] % 2 == target_parity:
                        zold_dates.append(curr)
                elif m in (1, 2, 12):
                    # Winter months: once a month (13 = 2nd Saturday, 24 = 4th Saturday)
                    target_nth = 2 if is_13 else 4
                    if curr == get_nth_weekday_of_month(curr.year, m, 5, target_nth):
                        zold_dates.append(curr)
            curr += timedelta(days=1)
    elif city == "Diósd":
        curr = start_date
        while curr <= end_date:
            if curr.weekday() == 0:  # Monday
                m = curr.month
                if 3 <= m <= 11:
                    # March to November: weekly
                    zold_dates.append(curr)
                else:
                    # Winter: 3rd Monday of the month
                    if curr == get_nth_weekday_of_month(curr.year, m, 0, 3):
                        zold_dates.append(curr)
            curr += timedelta(days=1)
    elif city == "Sóskút":
        curr = start_date
        while curr <= end_date:
            if curr.weekday() == 5:  # Saturday
                # Monthly: 3rd Saturday (March is skipped)
                if curr.month != 3 and curr == get_nth_weekday_of_month(curr.year, curr.month, 5, 3):
                    zold_dates.append(curr)
            curr += timedelta(days=1)
    elif city == "Tárnok":
        curr = start_date
        while curr <= end_date:
            if curr.weekday() == 0:  # Monday
                m = curr.month
                if 3 <= m <= 10:
                    # Bi-weekly on even ISO weeks
                    if curr.isocalendar()[1] % 2 == 0:
                        zold_dates.append(curr)
                else:
                    # Winter: 2nd Monday of the month
                    if curr == get_nth_weekday_of_month(curr.year, m, 0, 2):
                        zold_dates.append(curr)
            curr += timedelta(days=1)
    elif city == "Ráckeresztúr":
        curr = start_date
        while curr <= end_date:
            if curr.weekday() == 0:  # Monday
                # Monthly: 4th Monday (March and December are skipped)
                if curr.month not in (3, 12) and curr == get_nth_weekday_of_month(curr.year, curr.month, 0, 4):
                    zold_dates.append(curr)
            curr += timedelta(days=1)

    if zold_dates:
        schedule["zold"] = sorted(zold_dates)

    # 4. ÜVEG (Glass waste, currently Diósd and Tárnok)
    uveg_val = props.get("uveg")
    if uveg_val:
        u_str = str(uveg_val).lower().strip()
        day_match = re.search(r"([a-zöüóőúáéí]+)", u_str)
        week_match = re.search(r"(\d+)", u_str)
        if day_match and week_match:
            twday = DAYS_HU.get(day_match.group(1), 5)
            tnth = int(week_match.group(1))
            uveg_dates = []
            curr = start_date
            while curr <= end_date:
                if curr.weekday() == twday:
                    if curr == get_nth_weekday_of_month(curr.year, curr.month, twday, tnth):
                        uveg_dates.append(curr)
                curr += timedelta(days=1)
            if uveg_dates:
                schedule["uveg"] = sorted(uveg_dates)

    return schedule
