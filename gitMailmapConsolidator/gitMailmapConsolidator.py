# Note: beware, the tool is not working Well. I had something really helpful in mind:
# take the given output from `git shortlog -sne`, then find for all mail-adresses the best version and create matching
# replacements for "similar" adresses and names. Something like Levenstein-distance as metric, etc.
# But .. this needs time which I don't have.

import sys
import difflib
from collections import defaultdict


def process_input(input_data):
    """
    Process the input data from `git shortlog -sne`.

    :param list input_data: List of lines from `git shortlog -sne` output.
    :return: A dictionary with email as the key and a list of (count, name) as values.
    :rtype: dict
    """
    data = []
    for line in input_data:
        parts = line.strip().split()
        count = int(parts[0])
        name = ' '.join(parts[1:-1])
        email = parts[-1].strip('<>')
        data.append((count, name, email))

    email_map = defaultdict(list)
    for count, name, email in data:
        email_map[email].append((count, name))

    return email_map


def generate_mailmap(email_map):
    """
    Generate the .mailmap entries based on the processed data.

    :param dict email_map: Dictionary with email as key and list of (count, name) as values.
    :return: Consolidated .mailmap entries.
    :rtype: str
    """
    mailmap_entries = []

    for email, entries in email_map.items():
        entries.sort(reverse=True)  # Sort by count
        most_common_name = entries[0][1]
        print(f'"{most_common_name}" <{email}>')

        for _, name in entries:
            if name != most_common_name:
                similarity = difflib.SequenceMatcher(None, name, most_common_name).ratio()
                print(f'similarity: {similarity}')
                # If names are similar but not identical, create a mapping
                if similarity > 0.5: # and similarity < 1.0:
                    mailmap_entries.append(f"{most_common_name} <{email}> {name} <{email}>")
                    print("very similar")
                else:
                    print("no mapping")

    return "\n".join(mailmap_entries)


if __name__ == "__main__":
    """
    Main execution point. Takes input from stdin, processes it, and prints the .mailmap entries.
    """
    input_data = [line for line in sys.stdin]
    processed_data = process_input(input_data)
    mailmap = generate_mailmap(processed_data)
    print(mailmap)
