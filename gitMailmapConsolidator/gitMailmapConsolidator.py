import sys
from collections import defaultdict


def process_input(input_data):
    """
    Process the input data from `git shortlog -sne`.

    :param list input_data: List of lines from `git shortlog -sne` output.
    :return: A dictionary with email as the key and a list of (count, name) as values.
    :rtype: dict
    """
    # Store the count, name, and email
    data = []
    for line in input_data:
        parts = line.strip().split()
        count = int(parts[0])
        name = ' '.join(parts[1:-1])
        email = parts[-1].strip('<>')
        data.append((count, name, email))

    # Create a dictionary with email as the key and a list of (count, name) as values
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

        # Add the most common name-email pair as a "base" entry
        mailmap_entries.append(f"{most_common_name} <{email}>")

        # Map all other names and emails to the most common one
        for _, name in entries:
            if name != most_common_name:
                mailmap_entries.append(f"{most_common_name} <{email}> {name} <{email}>")

    return "\n".join(mailmap_entries)


if __name__ == "__main__":
    """
    Main execution point. Takes input from stdin, processes it, and prints the .mailmap entries.
    """
    input_data = [line for line in sys.stdin]
    processed_data = process_input(input_data)
    mailmap = generate_mailmap(processed_data)
    print(mailmap)
