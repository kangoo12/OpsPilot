"""Language validation and narrow positive evidence for immediate physical danger.

These checks constrain inference and reject violations; they never fabricate or
translate summaries or overwrite a model's classification after validation.
"""
import re

from app.customer_data import customer_language, language_prose, normalized, support_text

GREEK = r'\u0370-\u03ff\u1f00-\u1fff'


def foreign_tokens(message: str, language: str) -> list[str]:
    pattern = f'[{GREEK}]' if language == 'en' else '[A-Za-z]'
    return sorted({token for token in re.findall(r'\w[\w/-]*', support_text(message))
                   if re.search(pattern, token) and (any(char.isdigit() for char in token) or any(char.isupper() for char in token))},
                  key=lambda value: (-len(value), value))


def summary_pattern(message: str, language: str) -> str:
    # Only verbatim foreign-script tokens can occur within localized prose. This
    # preserves names/identifiers without admitting unrelated translated summaries.
    tokens = foreign_tokens(message, language)
    excluded = GREEK if language == 'en' else 'A-Za-z'
    unit = f'[^{excluded}]' + ('|' + '|'.join(re.escape(token) for token in tokens) if tokens else '')
    if language == 'en':
        return f'^(?:{unit})*$'
    return f'^(?:{unit})*[{GREEK}](?:{unit})*$'


def validate_summary_language(message: str, intent: str, reason: str) -> None:
    language = customer_language(message)
    tokens = foreign_tokens(message, language)
    for field in (intent, reason):
        prose = language_prose(field)
        for token in tokens:
            prose = re.sub(r'(?<!\w)' + re.escape(token) + r'(?!\w)', ' ', prose)
        greek = len(re.findall(f'[{GREEK}]', prose))
        latin = len(re.findall('[A-Za-z]', prose))
        if (language == 'en' and (greek > 0 or latin < 3)) or (language == 'el' and (greek < 3 or greek < latin)):
            raise ValueError('Summary language does not match customer language')


def immediate_physical_risk(message: str) -> bool:
    """Recognized current affirmative hazards, not generic return/hot-product words.

    Negated, past-resolved, hypothetical, quoted and explicit control clauses are
    conservatively excluded. This is finite evidence recognition, not full NLP.
    """
    text = normalized(support_text(message))
    text = re.sub(r'"[^"\n]*"|“[^”\n]*”', ' ', text)
    patterns = [
        r'\belectric(?:al)? shocks?\b|\belectrocut\w*\b|\bηλεκτροπληξ\w*\b',
        r'\b(?:on fire|caught fire|catching fire|smoking|giving off smoke|emitting smoke|smoke is coming out)\b',
        r'\b(?:charger|battery|device|adapter|socket|plug)\b.{0,45}\b(?:arcing|sparking|burning|melting)\b',
        r'\b(?:battery|power bank|cell)\b.{0,45}\b(?:swollen|swelling|bulging|leaking|hissing|venting|explod\w*|ruptur\w*)\b',
        r'\boverheat\w*\b.{0,45}\b(?:burn\w*|injur\w*|smoke|fire|melt\w*|too hot to touch)\b',
        r'\b(?:charger|device|battery|product)\b.{0,50}\b(?:burned my|burnt my|cut my|injured|caused an injury)\b',
        r'\bexposed (?:live|mains) wires?\b',
        r'\b(?:βγαζ\w*|βγηκ\w*)\b.{0,20}\b(?:καπνο|σπιθες)\b|\b(?:πηρε φωτια|καιγεται)\b',
        r'\bμπαταρ\w*\b.{0,40}\b(?:φουσκ\w*|διογκω\w*|εκραγ\w*|διαρρε\w*)\b',
        r'\bυπερθερμ\w*\b.{0,50}\b(?:εγκαυμα\w*|καπνο|φωτια|λιων\w*)\b',
        r'\b(?:συσκευη|φορτιστης|προιον)\b.{0,45}\b(?:προκαλεσε τραυματισμο|εκαψε το χερι|εκαψε το δαχτυλο)\b',
    ]
    excluded = r'\b(?:if|could|might|would|hypothetical|manual|warning label|(?:leaflet|label|guide).{0,25}(?:mentions?|warns?|describ\w*|discuss\w*)|used to|last year|months ago|resolved|repaired|can .* cause|is it possible|αν|υποθετικ|εγχειριδιο|παλια|περυσι|διορθωθηκε|αποκατασταθηκε|μπορει να)\b'
    for clause in re.split(r'[.!?;\n]|\bbut\b|\bαλλα\b', text):
        if re.search(excluded, clause):
            continue
        for pattern in patterns:
            for match in re.finditer(pattern, clause):
                before = clause[max(0, match.start() - 55):match.start()]
                if not re.search(r'\b(?:no|not|never|without|doesn.t|didn.t|isn.t|δεν|χωρις|καμια|καθολου)\s+(?:\w+\s+){0,3}$', before):
                    return True
    return False
