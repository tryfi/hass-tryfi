import datetime


def parse_fi_date(input: str | None) -> datetime.datetime | None:
    if not input:
        return None
    return datetime.datetime.fromisoformat(input.replace("Z", "+00:00"))
