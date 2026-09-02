import os

CARDS_FILE = "cards.txt"

def pop_card():
    """Pops the top card from cards.txt and deletes it from the file."""
    if not os.path.exists(CARDS_FILE):
        return None

    with open(CARDS_FILE, "r") as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    card_data = None
    remaining_lines = []
    card_found = False

    for line in lines:
        if line.startswith("#"):
            remaining_lines.append(line)
            continue

        if not card_found:
            # Handle comma, pipe, or space delimiters
            delim = "," if "," in line else ("|" if "|" in line else " ")
            parts = [p.strip() for p in line.split(delim)]

            if len(parts) >= 4:
                card_number = parts[0]
                exp_raw = parts[1] # e.g. "08/30" or "08,30"
                cvv = parts[2]
                zip_code = parts[3] if len(parts) > 3 else "90250"

                # Parse MM/YY safely
                if "/" in exp_raw:
                    exp_month, exp_year = exp_raw.split("/")
                else:
                    exp_month = exp_raw[:2]
                    exp_year = exp_raw[2:]

                card_data = {
                    "number": card_number,
                    "exp_month": exp_month.zfill(2),
                    "exp_year": exp_year[-2:],
                    "cvv": cvv,
                    "zip": zip_code
                }
                card_found = True
                continue  # Skip adding so it is removed from the file

        remaining_lines.append(line)

    if card_found:
        with open(CARDS_FILE, "w") as f:
            for l in remaining_lines:
                f.write(f"{l}\n")

    return card_data