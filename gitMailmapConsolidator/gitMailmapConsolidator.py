import sys
from collections import defaultdict


def process_input(input_data):
    # Store the count, name, and email
    data = []
    for line in input_data:
        parts = line.strip().split("\t")
        count = int(parts[0])
        name, email = parts[1].rsplit(' ', 1)
        email = email.strip('<>')
        data.append((count, name, email))

    # Create a dictionary with email as the key and a list of (count, name) as values
    email_map = defaultdict(list)
    for count, name, email in data:
        email_map[email].append((count, name))

    # Determine the most common name for each email
    result = {}
    for email, entries in email_map.items():
        entries.sort(reverse=True)  # Sort by count
        most_common_name = entries[0][1]
        result[most_common_name] = email

    return result


def generate_mailmap(data):
    mailmap_entries = []
    for name, email in data.items():
        mailmap_entries.append(f"{name} <{email}>")

    return "\n".join(mailmap_entries)


if __name__ == "__main__":
    input_data = [line for line in sys.stdin]
    processed_data = process_input(input_data)
    mailmap = generate_mailmap(processed_data)
    print(mailmap)
