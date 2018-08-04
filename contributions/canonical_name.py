EMAIL_MAP = {"greg@krypto.org": "Gregory P. Smith"}

NAME_MAP = {}


def canonical_name(name, email):
    if email in EMAIL_MAP:
        return EMAIL_MAP[email]

    if name in NAME_MAP:
        return NAME_MAP[name]

    return name
