# Copyright (c) 2025, Kartoza and contributors
# For license information, please see license.txt

from typing import Any, Dict, List
import frappe
from frappe.model.document import Document


class BitemporalAnalysis(Document):
    pass


@frappe.whitelist()
def get_import_rows(import_name: str) -> Dict[str, Any]:
    if not import_name:
        return {"rows": []}
    parent = frappe.get_doc("Bitemporal Import", import_name)
    rows = []
    from datetime import datetime
    for c in parent.rows or []:
        vto = c.valid_to
        if not vto:
            vto = datetime(9999, 1, 1, 0, 0, 0)
        rows.append({
            "branch_seq": c.branch_seq,
            "transaction_time": c.transaction_time,
            "valid_from": c.valid_from,
            "valid_to": vto,
            "date": c.date,
            "journal_id": c.journal_id,
            "prior_tx_ref": c.prior_tx_ref,
            "self_tx_ref": c.self_tx_ref,
            "transaction_id": c.transaction_id,
            "reason": c.reason,
            "worker": c.worker,
            "company": c.company,
            "country": c.country,
            "action": c.action,
            "drcr": c.drcr,
            "amount": c.amount,
            "currency": c.currency,
        })
    return {"rows": rows, "meta": {"source_file": parent.source_file_name, "count": len(rows)}}
