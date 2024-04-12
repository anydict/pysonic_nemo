import re
from typing import Union


def fix_iso_timestamp(var_time: Union[str, None]) -> str:
    """ Converting the date to the correct string format """

    if isinstance(var_time, str) and '+' in var_time:
        # 2023-05-16T00:33:52.951+0300 to 2023-05-16T00:33:52.951000
        return f'{var_time[:23]}000'
    elif isinstance(var_time, str) and len(var_time) == 26 and 'T' not in var_time:
        # 2023-05-16 00:33:52.951+0300 to 2023-05-16T00:33:52.951000
        return var_time.replace(' ', 'T')
    elif isinstance(var_time, str) and len(var_time) == 26 and 'T' in var_time:
        # if correct return raw
        return var_time
    else:
        # if invalid return empty string
        return ''


def if_null(var, val):
    # print('if_null', if_null(None, 123))
    if var is None:
        return val
    return var


def is_like(text, pattern) -> bool:
    # print('is_like', is_like('TEST123', 'TEST%'))
    if '%' in pattern:
        pattern = pattern.replace('%', '.*?')
    if '_' in pattern:
        pattern = pattern.replace('_', '.')
    if re.match(pattern, text):
        return True
    return False


def is_not_like(text, pattern) -> bool:
    # print('is_not_like', is_not_like('TEST123', 'PEP%'))
    return not is_like(text, pattern)


def regexp_substr(text: str, pattern: str, position: int = 0, occurrence: int = 0) -> str:
    # print('regexp_substr', regexp_substr('TEST123', '^TEST.[0-9]'))
    s = text[position:]
    search_result = re.search(pattern, s)
    if search_result:
        return search_result.group(occurrence)
    return ''


def regexp_like(text: str, pattern: str, position: int = 0) -> bool:
    # print('regexp_like', regexp_like('TEST123', '^TEST.[0-9]'))
    s = text[position:]
    if re.match(pattern, s):
        return True
    return False


def coalesce(iterable, empty_string_is_none: bool = False):
    # print('coalesce', coalesce([None, 'TEST123', 321]))
    for el in iterable:
        if el is not None:
            if empty_string_is_none and el == '':
                continue
            return el
    return None
