"""Conservatively mask explicit output-control spans; never treat this as a trust boundary.

Original messages stay intact. Models, schemas, evidence checks and human review
remain responsible for their own validation; this only reduces candidate pollution.
"""
import re
import unicodedata


def normalized(value: str) -> str:
    return ''.join(char for char in unicodedata.normalize('NFD', value.lower())
                   if unicodedata.category(char) != 'Mn')


def support_text(message: str) -> str:
    text = re.sub(r'<(system|developer)>[\s\S]*?</\1>|\[(SYSTEM|DEVELOPER)\][\s\S]*?\[/\2\]',
                  lambda match: ' ' * len(match[0]), message, flags=re.I)
    clauses = re.split(r'(?<=[.!?;\n])', text)
    control = r'\b(?:system override|developer instruction|system\s*:|ignore (?:all |every |the |any |previous )*(?:instructions|rules|policies)|(?:set|output|fabricate|invent|replace)\b.{0,45}\b(?:category|priority|order.?id)|εντολη (?:συστηματος|διαχειριστη)|αγνοησε.{0,55}(?:κανον|προηγουμεν|προβλημα)|παρακαμψε.{0,30}κανον|κατασκευασε|(?:γραψε|βαλε|αλλαξε).{0,35}(?:urgent|payments|other|low|order.?id))'
    return ''.join(' ' * len(clause) if re.search(control, normalized(clause)) else clause for clause in clauses)


def security_topic(message: str, category: str) -> str | None:
    text = normalized(support_text(message))
    if category == 'payments' and re.search(r'unauthori[sz]ed|unrecogni[sz]ed|without (?:my |any )?(?:consent|permission)|card (?:fraud|stolen)|did not (?:authori[sz]e|make)|μη (?:εγκεκριμεν|εξουσιοδοτημεν)|χωρις.{0,20}(?:αδεια|εγκριση)|δεν.{0,15}ενεκρινα', text):
        return 'card'
    if category == 'technical_support' and re.search(r'account.{0,40}(?:compromis|hack|intrud)|intruder|stolen (?:password|session)|(?:password|recovery address).{0,40}(?:without|changed)|παραβιασ|χωρις αδεια.{0,35}(?:κωδικ|λογαριασ)|καποιος.{0,30}αλλαξε.{0,30}(?:κωδικ|email)', text):
        return 'account'
    return None


def customer_language(message: str) -> str:
    text = language_prose(support_text(message))[:500]
    greek = len(re.findall(r'[\u0370-\u03ff\u1f00-\u1fff]', text))
    latin = len(re.findall(r'[A-Za-z]', text))
    return 'el' if greek >= 3 and greek >= latin else 'en'


def language_prose(text: str) -> str:
    """Ignore URLs/emails and digit-bearing identifiers only for language counting."""
    text = re.sub(r'https?://\S+|\b\S+@\S+\b', ' ', text)
    return re.sub(r'\b\w[\w/-]*\b', lambda match: ' ' if any(char.isdigit() for char in match[0]) else match[0], text)
