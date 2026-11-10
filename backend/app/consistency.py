"""Conservative checks of explicit Greek/English claims against an order snapshot.

Customer claims are evidence to compare, never instructions or verified facts.
These checks do not decide which source is correct or infer a cause. Unrecognized
wording is not proof of agreement; the UI calls it 'no discrepancy detected'.
"""
import re
from typing import Literal
import unicodedata

from pydantic import BaseModel, Field


class ConsistencyIssue(BaseModel):
    code: Literal["product_mismatch", "delivery_status_mismatch", "conflicting_customer_statements", "order_unknown", "order_not_provided"]
    message: str
    customer_reported: str | None = None
    order_recorded: str | None = None


class ConsistencyCheck(BaseModel):
    status: Literal["consistent", "discrepancy", "unknown_order", "no_order_id", "not_checked"] = "not_checked"
    requires_human_review: bool = True
    issues: list[ConsistencyIssue] = Field(default_factory=list)
    reported_products: list[str] = Field(default_factory=list)
    reported_delivery_states: list[str] = Field(default_factory=list)
    check_version: str = "reported-facts-v1"


PRODUCT_WORDS = {
    "smartphone": r"smart\s?phones?|cell\s?phones?|mobile\s+phones?|phones?|κινητ[οα](?:\s+τηλεφων[οα])?|τηλεφων[οα]",
    "lamp": r"lamps?|reading\s+lights?|φωτιστικ[οα]|λαμπ(?:α|ες)",
    "headphones": r"headphones?|earphones?|ακουστικ[οα]",
    "keyboard": r"keyboards?|πληκτρολογι[οα]",
    "mouse": r"mouse|mice|ποντικι[α]?",
    "speaker": r"speakers?|ηχει[οα]",
    "mug": r"mugs?|κουπ(?:α|ες)",
    "laptop stand": r"laptop\s+stands?|βαση\s+(?:για\s+)?laptop",
    "monitor riser": r"monitor\s+risers?|βαση\s+οθονης",
    "throw": r"throws?|ριχταρι[α]?",
    "notebook": r"notebooks?|τετραδι[οα]",
    "backpack": r"backpacks?|σακιδι[οα]",
    "fan": r"fans?|ανεμιστηρ(?:ας|ες)",
    "bottle": r"bottles?|μπουκαλι[α]?",
    "mat": r"yoga\s+mats?|στρωμα\s+γιογκα",
    "hub": r"usb\s+hubs?|usb\s+hub",
    "scale": r"(?:kitchen\s+)?scales?|ζυγαρι[αες]+",
    "jars": r"jars?|βαζ[οα]",
}


def normalize(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFD", value.lower().replace("’", "'"))
                   if unicodedata.category(char) != "Mn")


def products_in(value: str) -> set[str]:
    text = normalize(value)
    # An ID such as DEMO-LAMP-9001 is a reference, not a product assertion.
    text = re.sub(r"\b\w+(?:[-/]\w+)+\b", lambda match: " " if any(char.isdigit() for char in match[0]) else match[0], text)
    products = set()
    for product, pattern in PRODUCT_WORDS.items():
        for match in re.finditer(r"\b(?:" + pattern + r")\b", text):
            before = text[max(0, match.start() - 45):match.start()]
            # Exclude explicit negation and common incidental uses of a phone.
            if re.search(r"(?:not\s+(?:(?:a|an|the|my)\s+)?|δεν\s+ειναι\s+(?:(?:το|ενα)\s+)?)$", before):
                continue
            if product == "smartphone" and re.search(r"(?:(?:using|via|on|from)\s+(?:(?:a|the|my)\s+)?|(?:γραφω απο|χρησιμοποιωντας)\s+(?:(?:το|ενα)\s+)?)$", before):
                continue
            products.add(product)
    return products


def delivery_claims(value: str) -> set[str]:
    text = normalize(value)
    states = set()
    # Negative receipt and affirmative receipt are collected independently. A
    # message containing both must be reconciled, not resolved by picking one.
    negative = r"\b(?:not|never|hasn't|haven't|didn't|isn't|wasn't|δεν)\b[^.!?;\n]{0,45}\b(?:arriv(?:e|ed)|receiv(?:e|ed)|delivered|παρελαβα|παραλαβει|παραλαβαμε|φτασει|εφτασε|παραδοθηκε|παραδοθει)\b"
    if re.search(negative, text) or re.search(r"\b(?:still waiting for (?:my|the) (?:order|package|parcel)|ακομα περιμενω την παραγγελια)\b", text):
        states.add("not_received")
    for match in re.finditer(r"\b(?:delivered|arrived|received|παρελαβα|παραλαβαμε|παραδοθηκε|εφτασε)\b", text):
        before = text[max(0, match.start() - 60):match.start()]
        after = text[match.end():match.end() + 90]
        clause_before = re.split(r"[.!?;\n]|\bbut\b|\bαλλα\b", before)[-1]
        if re.search(r"\b(?:not|never|hasn't|haven't|didn't|isn't|wasn't|δεν|ποτε|will|when|whether|if|θα|ποτε|αν)\b", clause_before):
            continue
        if re.match(r"\s*(?:has|have|did|is|was|were)\b", clause_before) and re.match(r"[^.!?;\n]*\?", after):
            continue
        # Don't mistake a received email or a question about delivery for a parcel.
        scope = clause_before + " " + after
        if re.search(r"\b(?:order|package|parcel|item|it|phone|smartphone|lamp|παραγγελια|δεμα|κινητο|προιον|φωτιστικο)\b", scope):
            if not re.match(r"\s+(?:(?:an?|the|my)\s+)?(?:email|message|notification)\b", after):
                states.add("received")
    if re.search(r"\b(?:hasn't|not|never)\s+(?:been\s+)?shipped\b|\bδεν\s+εχει\s+αποσταλει\b", text):
        states.add("not_shipped")
    if re.search(r"\b(?:is in transit|was shipped|has shipped|has been shipped|σε μεταφορα)\b", text):
        states.add("shipped")
    return states


def check_consistency(message: str, order, reference_order_id: str | None) -> ConsistencyCheck:
    products = products_in(message)
    states = delivery_claims(message)
    issues = []
    if len(products) > 1 or {"received", "not_received"} <= states or {"shipped", "not_shipped"} <= states:
        issues.append(ConsistencyIssue(
            code="conflicting_customer_statements", message="The message contains competing product or delivery statements. Human review must reconcile them.",
            customer_reported=", ".join(sorted(products | states)),
        ))
    if order:
        recorded_products = products_in(order.product)
        if products and recorded_products and not products <= recorded_products:
            issues.append(ConsistencyIssue(
                code="product_mismatch", message="The product reported in the message differs from the matched order record. Neither source has been reconciled.",
                customer_reported=", ".join(sorted(products)), order_recorded=order.product,
            ))
        mismatch = ("received" in states and order.delivery_status != "delivered") or (
            "not_received" in states and order.delivery_status in {"delivered", "returned"}
        ) or ("not_shipped" in states and order.delivery_status in {"in_transit", "delivered", "returned"}) or (
            "shipped" in states and order.delivery_status in {"processing", "cancelled"}
        )
        if mismatch:
            issues.append(ConsistencyIssue(
                code="delivery_status_mismatch", message="The delivery information reported in the message differs from the matched order record. Human review is required.",
                customer_reported=", ".join(sorted(states)), order_recorded=order.delivery_status,
            ))
    else:
        issues.append(ConsistencyIssue(
            code="order_unknown" if reference_order_id else "order_not_provided",
            message="No matching order record is available; order facts cannot be verified." if reference_order_id else "No order reference is available; order facts cannot be verified.",
        ))
    material = any(issue.code in {"product_mismatch", "delivery_status_mismatch", "conflicting_customer_statements"} for issue in issues)
    status = "discrepancy" if material else "consistent" if order else "unknown_order" if reference_order_id else "no_order_id"
    return ConsistencyCheck(status=status, requires_human_review=bool(issues), issues=issues,
                            reported_products=sorted(products), reported_delivery_states=sorted(states))
