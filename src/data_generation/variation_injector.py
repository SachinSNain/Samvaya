"""
Injects realistic noise into business names, addresses, and identifiers
to simulate cross-department data-entry inconsistencies.
"""
import random
import string

from .dictionaries.karnataka_street_names import LANDMARKS

ADJACENT_KEYS = {
    'a': 'sqwz', 'b': 'vghn', 'c': 'xdfv', 'd': 'serfcx', 'e': 'wsdr',
    'f': 'drtgvc', 'g': 'ftyhbv', 'h': 'gyujnb', 'i': 'ujko', 'j': 'huikmn',
    'k': 'jiolm', 'l': 'kop', 'm': 'njk', 'n': 'bhjm', 'o': 'iklp',
    'p': 'ol', 'q': 'wa', 'r': 'edft', 's': 'awedxz', 't': 'rfgy',
    'u': 'yhji', 'v': 'cfgb', 'w': 'qase', 'x': 'zsdc', 'y': 'tghu',
    'z': 'asx',
}

LEGAL_SUFFIX_VARIANTS = {
    "Private Limited": [
        "Pvt Ltd", "P Ltd", "Pvt. Ltd.", "Private Ltd", "Pvt.Ltd", "PVT LTD"], "Limited": [
            "Ltd", "Ltd.", "LTD"], "Limited Liability Partnership": [
                "LLP", "L.L.P"], "& Co.": [
                    "and Co.", "& Company", "& Co"], "& Sons": [
                        "and Sons", "& Son"], "Enterprises": [
                            "Entr.", "Enterp."], "Industries": [
                                "Inds", "Inds.", "INDS", "Indus"], }

WORD_ABBREVIATIONS = {
    "Industries": ["Inds", "Inds.", "INDS", "Indus"],
    "Manufacturing": ["Mfg", "Mfg.", "MFG"],
    "Engineering": ["Engg", "Engg.", "Eng"],
    "Bengaluru": ["Bangalore", "B'lore", "BLR", "Blore", "Bangalore"],
    "Karnataka": ["KA", "Karn."],
    "International": ["Intl", "Int'l"],
    "Exports": ["Expts", "Exp"],
    "Granites": ["Granits", "Grantz"],
    "Technologies": ["Tech", "Techno", "Techs"],
    "Solutions": ["Soln", "Solns"],
    "Services": ["Serv.", "Svcs"],
    "Associates": ["Assoc.", "Assocs"],
    "Enterprises": ["Entr.", "Ent"],
    "Traders": ["Trdrs", "Tradrs"],
    "Distributors": ["Distrib.", "Dist"],
}

TRANSLITERATION_VARIANTS = {
    "Srinivasa": ["Shrinivasa", "Sreenivasa", "Sriniwasa", "Sreenivaasa"],
    "Venkatesh": ["Venkataish", "Venkatesa", "Venkatesh"],
    "Manjunath": ["Manjunatha", "Munjunath", "Manjnath"],
    "Shivaraju": ["Shiva Raju", "Sivaraju", "Siva Raju"],
    "Basavaraj": ["Basava Raj", "Basavaraju", "Basavraj"],
    "Thimmappa": ["Thimappa", "Timmappa", "Thimapa"],
    "Hanumantha": ["Hanumanta", "Hanumant", "Anumantha"],
    "Muniswamy": ["Munisamy", "Muniswami", "Munisawmy"],
}


def inject_name_variation(name: str) -> str:
    result = name

    # Legal suffix swap (~30%)
    if random.random() < 0.30:
        for canonical, variants in LEGAL_SUFFIX_VARIANTS.items():
            if canonical in result:
                result = result.replace(canonical, random.choice(variants), 1)
                break

    # Word abbreviation (~25%)
    if random.random() < 0.25:
        words = result.split()
        new_words = []
        for word in words:
            if word in WORD_ABBREVIATIONS and random.random() < 0.6:
                new_words.append(random.choice(WORD_ABBREVIATIONS[word]))
            else:
                new_words.append(word)
        result = " ".join(new_words)

    # Transliteration variant (~10%)
    if random.random() < 0.10:
        for canonical, variants in TRANSLITERATION_VARIANTS.items():
            if canonical in result:
                result = result.replace(canonical, random.choice(variants), 1)
                break

    # Typo injection (~15%)
    if random.random() < 0.15:
        result = _inject_typo(result)

    # Case variation (~20%)
    if random.random() < 0.20:
        result = random.choice(
            [result.upper(), result.lower(), result.title()])

    return result


def _inject_typo(text: str) -> str:
    if len(text) < 4:
        return text
    op = random.choice(["swap_chars", "delete_char",
                       "double_char", "adjacent_key"])
    chars = list(text)
    pos = random.randint(1, len(chars) - 2)

    if op == "swap_chars" and pos + 1 < len(chars):
        chars[pos], chars[pos + 1] = chars[pos + 1], chars[pos]
    elif op == "delete_char":
        chars.pop(pos)
    elif op == "double_char":
        chars.insert(pos, chars[pos])
    elif op == "adjacent_key":
        c = chars[pos].lower()
        if c in ADJACENT_KEYS:
            replacement = random.choice(ADJACENT_KEYS[c])
            chars[pos] = replacement.upper(
            ) if chars[pos].isupper() else replacement

    return "".join(chars)


def inject_address_variation(
        entity_address: dict,
        format_index: int = None) -> str:
    e = entity_address
    pin = e["pin_code"]
    building = e["building"]
    street = e["street"]
    locality = e["locality"]
    industrial_area = e.get("industrial_area") or "Industrial Area"

    formats = [
        lambda: f"#{building}, {street}, {locality}, Bengaluru - {pin}",
        lambda: f"{building}, {industrial_area}, {locality}, Bengaluru {pin}",
        lambda: f"Sy. No. {random.randint(100, 300)}/{random.randint(1, 10)}, {locality}, {pin}",
        lambda: f"Near {random.choice(LANDMARKS)}, {locality}, Bengaluru",
        lambda: f"{locality}, Bengaluru - {pin}",
        lambda: f"{building}, {street}, {locality}, {e['taluk']}, {e['district']} - {pin}",
    ]

    idx = format_index if format_index is not None else random.randint(
        0, len(formats) - 1)
    return formats[idx % len(formats)]()


def inject_pan(true_pan, presence_rate: float):
    if true_pan is None:
        return None
    if random.random() > presence_rate:
        return None
    if random.random() < 0.03:
        pos = random.randint(5, 8)
        corrupt = random.choice(string.ascii_uppercase + string.digits)
        return true_pan[:pos] + corrupt + true_pan[pos + 1:]
    return true_pan


def inject_gstin(true_gstin, pan_in_record):
    if true_gstin is None:
        return None
    if pan_in_record is None:
        return None if random.random() < 0.70 else true_gstin
    if random.random() < 0.15:
        return None
    if random.random() < 0.02:
        pos = random.randint(2, 14)
        corrupt = random.choice(string.ascii_uppercase + string.digits)
        return true_gstin[:pos] + corrupt + true_gstin[pos + 1:]
    return true_gstin


def inject_owner_name_variation(owner_name: str) -> str:
    parts = owner_name.split()
    if len(parts) < 2:
        return owner_name
    variations = [
        lambda p: f"{p[0]} {p[1]}",
        lambda p: f"{p[0][0]}. {p[1]}",
        lambda p: f"{p[0]} {p[1][0]}.",
        lambda p: f"{p[1]}, {p[0]}",
        lambda p: f"{p[0].upper()} {p[1].upper()}",
        lambda p: " ".join(p),
    ]
    return random.choice(variations)(parts)


def inject_phone_variation(phone: str):
    if random.random() < 0.15:
        return None
    if random.random() < 0.10:
        formats = [
            f"+91-{phone}", f"0{phone}",
            f"{phone[:5]}-{phone[5:]}", f"+91 {phone}",
        ]
        return random.choice(formats)
    return phone
