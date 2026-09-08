import os

DATA_DIR = "/app/data" if os.path.exists("/app/data") else "."
CARDS_FILE = os.path.join(DATA_DIR, "cards.txt")

def pop_card():
    """
    Pops a card from cards.txt.
    Allows each card to be used twice before removing it from the file.
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
            raw_line = line
            use_count = 0
            # Track uses via trailing suffix: ;uses=N
            if ";uses=" in line:
                parts_use = line.split(";uses=")
                raw_line = parts_use[0].strip()
                try:
                    use_count = int(parts_use[1].strip())
                except ValueError:
                    use_count = 0

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

                use_count += 1
                # Keep the card in the file if used less than 2 times
                if use_count < 2:
                    remaining_lines.append(f"{raw_line};uses={use_count}")
                continue

        remaining_lines.append(line)

    if card_found:
        with open(CARDS_FILE, "w") as f:
            for l in remaining_lines:
                f.write(f"{l}\n")

    return card_data