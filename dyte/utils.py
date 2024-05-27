import re

# preset types
GROUP_CALL_PARTICIPANT = "group_call_participant"
GROUP_CALL_HOST = "group_call_host"


def replace_special_chars(s: str) -> str:
    """
    Replace all special characters in the input string with underscores.

    Special characters are defined as any character that is not a
    letter, digit, or whitespace. This also includes the '+' character.

    Parameters:
    s (str): The input string to be processed.

    Returns:
    str: The processed string with special characters replaced by underscores.

    Example:
    >>> replace_special_chars("Hello, World! +")
    'Hello__World___'
    """
    # Define the regex pattern to match special characters
    pattern = r"[^a-zA-Z0-9\s]"

    # Replace all matches of the pattern with '_'
    return re.sub(pattern, "_", s)
