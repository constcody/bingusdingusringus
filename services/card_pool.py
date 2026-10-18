import os

DATA_DIR = "/app/data" if os.path.exists("/app/data") else "."
CARDS_FILE = os.path.join(DATA_DIR, "cards.txt")


def pop_card():
    """
    Pops a card from cards.txt.
    Removes the card from the file immediately after 1 use.
    """
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
            # Strip any legacy ;uses=N suffix if still present in cards.txt
            raw_line = line.split(";uses=")[0].strip() if ";uses=" in line else line

            delim = "," if "," in raw_line else ("|" if "|" in raw_line else " ")
            parts = [p.strip() for p in raw_line.split(delim)]

            if len(parts) >= 4:
                card_number = parts[0]
                exp_raw = parts[1]
                cvv = parts[2]
                zip_code = parts[3] if len(parts) > 3 else "90250"

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
                # Do not append to remaining_lines so it is removed after 1 use
                continue

        remaining_lines.append(line)

    if card_found:
        with open(CARDS_FILE, "w") as f:
            for l in remaining_lines:
                f.write(f"{l}\n")

    return card_data