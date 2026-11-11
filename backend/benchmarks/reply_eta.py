"""Fact-aware delivery ETA rubric v2, separate from frozen 5B assertions."""
import re


def evaluate_delivery_eta(context: dict, output: str, language: str) -> dict:
    dates = set(re.findall(r'\b\d{4}-\d{2}-\d{2}\b', output))
    order = context.get('order')
    if not order or context.get('consistency', {}).get('status') == 'discrepancy':
        return {'version': 2, 'passed': not dates, 'basis': 'No order-specific dates may be asserted for unknown/disputed data.'}
    eta = order.get('estimated_delivery_date')
    allowed = {str(order.get(key)) for key in ['order_date', 'snapshot_date', 'estimated_delivery_date']}
    if dates - allowed:
        return {'version': 2, 'passed': False, 'basis': 'Output contains a date outside the verified record.'}
    if eta:
        caveat = 'not a delivery guarantee' if language == 'en' else 'όχι για εγγύηση'
        return {'version': 2, 'passed': eta in output and caveat in output,
                'basis': 'Known ETA must match the verified date and remain an estimate.'}
    if order.get('delivery_status') in {'delivered', 'cancelled', 'returned'}:
        return {'version': 2, 'passed': True, 'basis': 'No ETA exists; a completed/closed status does not require an ETA sentence.'}
    unknown = 'No estimated delivery date is available' if language == 'en' else 'Δεν υπάρχει επιβεβαιωμένη εκτιμώμενη ημερομηνία'
    return {'version': 2, 'passed': unknown in output,
            'basis': 'No verified ETA exists: explicitly preserve the unknown date rather than requiring an estimate caveat.'}
