# Copyright (c) 2025, Kartoza and contributors
# For license information, please see license.txt

import csv
import io
import json
import re
from typing import List, Dict, Any

import frappe
from frappe.model.document import Document
from frappe.utils.file_manager import get_file
from frappe.utils import get_datetime, getdate
from datetime import datetime, timezone

BITEMP_ROW_CHILD = "Bitemporal Import Row"


class BitemporalImport(Document):
    def validate(self):
        # nothing heavy here; parsing is user-triggered via button
        pass

    def clear_rows(self):
        self.set("rows", [])

    def set_summary(self, file_name: str, count: int):
        self.source_file_name = file_name
        self.rows_count = count


@frappe.whitelist()
def parse_file(docname: str, file_url: str | None = None, input_type: str | None = None) -> Dict[str, Any]:
    """Parse the attached file (CSV/JSON) and populate child rows.

    Accepts optional file_url and input_type to work with unsaved form values.
    """
    doc = frappe.get_doc("Bitemporal Import", docname)

    # prefer passed file_url to allow parsing without saving the form first
    file_url = file_url or doc.upload
    if not file_url:
        frappe.throw("Please attach a file first")

    # get file content
    file_doc = get_file(file_url)
    file_name = file_doc[0]
    content_raw = file_doc[1]
    text = _ensure_text(content_raw)

    # decide parser: prefer explicit input_type; otherwise auto-detect
    itype = (input_type or doc.input_type or "CSV").upper()
    # auto-detect JSON if content starts with object/array markers (account for BOM)
    lead = text.lstrip("\ufeff \t\r\n")[:1]
    if itype == "CSV" and lead in ("{", "["):
        itype = "JSONS"

    rows: List[Dict[str, Any]]
    if itype == "CSV":
        rows = _parse_csv_text(text)
    else:
        rows = _parse_json_text(text)

    # normalize and populate child table
    doc.clear_rows()
    last_currency: str | None = None
    for r in rows:
        child = doc.append("rows", {})
        child.branch_seq = _to_int(r.get("branchSeq") or r.get("branch_seq"))
        child.transaction_time = _to_dt(r.get("transactionTime") or r.get("transaction_time"))
        child.valid_from = _to_dt(r.get("fromDate") or r.get("valid_from"))
        _raw_valid_to = r.get("toDate") or r.get("valid_to")
        if _raw_valid_to in (None, "", "EndOfTime"):
            child.valid_to = datetime(9999, 1, 1, 0, 0, 0)
        else:
            child.valid_to = _to_dt(_raw_valid_to)
        child.date = _to_date(r.get("date"))
        child.journal_id = _to_text(r.get("journalId") or r.get("journal_id"))
        child.prior_tx_ref = _to_text(r.get("priorTxRef") or r.get("prior_tx_ref"))
        child.self_tx_ref = _to_text(r.get("selfTxRef") or r.get("self_tx_ref"))
        child.transaction_id = _to_int(r.get("transactionId") or r.get("transaction_id"))
        child.reason = _to_text(r.get("reason"))
        child.worker = _to_text(r.get("worker"))
        child.company = _to_text(r.get("company"))
        child.country = _to_text(r.get("country"))
        child.action = _to_text(r.get("action"))
        child.drcr = _to_text(r.get("drcr"))
        child.amount = _to_float(r.get("amount"))
        curr = _to_text(r.get("currency"))
        if not curr:
            curr = last_currency
        child.currency = curr
        if curr:
            last_currency = curr

    if not rows:
        try:
            # Minimal diagnostics to server log to aid troubleshooting
            preview = text.strip().splitlines()[:1]
            first = preview[0] if preview else ''
            diag: Dict[str, Any] = {
                "lead": lead,
                "input_type": itype,
                "first_line_prefix": first[:200]
            }
            # Try decode store-like doc for the first line
            try:
                item0 = json.loads(first)
                doc0 = _decode_store_like_item(item0)
                if isinstance(doc0, dict):
                    diag.update({
                        "doc_keys": list(doc0.keys()),
                        "branchSeq": doc0.get("branchSeq"),
                        "has_entries": isinstance(doc0.get("entries"), (dict, list)),
                    })
            except Exception:
                pass
            frappe.log_error(message=json.dumps(diag, default=str), title="Bitemp JSON parse returned 0 rows")
        except Exception:
            pass

    doc.set_summary(file_name, len(rows))
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "rows": len(rows)}


@frappe.whitelist()
def load_example(docname: str) -> Dict[str, Any]:
    """Load a tiny in-memory example for quick demo."""
    doc = frappe.get_doc("Bitemporal Import", docname)
    csv_str = "branchSeq,transactionTime,fromDate,toDate,reason,action,drcr,amount\n" \
              "100,2025-03-31T17:00:00Z,2025-03-31T17:00:00Z,EndOfTime,Post earnings (original),salary,dr,21175\n" \
              "100,2025-03-31T17:00:00Z,2025-03-31T17:00:00Z,EndOfTime,Post earnings (original),salary,cr,21175\n"
    rows = _parse_csv_text(csv_str)
    doc.clear_rows()
    for r in rows:
        child = doc.append("rows", {})
        child.branch_seq = _to_int(r.get("branchSeq"))
        child.transaction_time = _to_dt(r.get("transactionTime"))
        child.valid_from = _to_dt(r.get("fromDate"))
        _raw_valid_to = r.get("toDate")
        if _raw_valid_to in (None, "", "EndOfTime"):
            child.valid_to = datetime(9999, 1, 1, 0, 0, 0)
        else:
            child.valid_to = _to_dt(_raw_valid_to)
        child.reason = _to_text(r.get("reason"))
        child.action = _to_text(r.get("action"))
        child.drcr = _to_text(r.get("drcr"))
        child.amount = _to_float(r.get("amount"))
    doc.set_summary("example.csv", len(rows))
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "rows": len(rows)}


# helpers

def _parse_csv_text(text: str) -> List[Dict[str, Any]]:
    # normalize newlines and parse
    text = text.replace("\r\n", "\n").strip("\n")
    lines = text.splitlines()
    if not lines:
        return []
    f = io.StringIO(text)
    reader = csv.DictReader(f)
    out: List[Dict[str, Any]] = []
    for idx, row in enumerate(reader):
        cleaned = {k.strip(): _clean_field(v) for k, v in row.items() if k}
        # Fallback: extract action, drcr, amount, currency from the raw line tail
        # Header is line 0; data starts at 1
        raw_line = lines[idx + 1] if idx + 1 < len(lines) else None
        if raw_line:
            tail_parts = raw_line.rsplit(',', 4)
            if len(tail_parts) == 5:
                _, action_raw, drcr_raw, amount_raw, currency_raw = tail_parts
                action_raw = _clean_field(action_raw)
                drcr_raw = _clean_field(drcr_raw)
                amount_raw = _clean_field(amount_raw)
                currency_raw = _clean_field(currency_raw)
                # Fill when missing or clearly bad
                if not cleaned.get('action'):
                    cleaned['action'] = action_raw
                if not cleaned.get('drcr'):
                    cleaned['drcr'] = drcr_raw
                # If amount parsed later would be None, prefer tail
                if not cleaned.get('amount') or str(cleaned.get('amount')).strip() == '':
                    cleaned['amount'] = amount_raw
                if not cleaned.get('currency'):
                    cleaned['currency'] = currency_raw
        out.append(cleaned)
    return out


def _parse_json_text(text: str) -> List[Dict[str, Any]]:
    """Parse JSON text as either a single JSON (array or object with rows) or NDJSON.

    Returns only dict-shaped rows; other shapes are ignored.
    """
    def _normalize_loaded(data: Any) -> List[Dict[str, Any]]:
        if isinstance(data, dict):
            rows = data.get("rows", data.get("data", data.get("items", [])))
            if isinstance(rows, list):
                return [r for r in rows if isinstance(r, dict)]
            # if dict without rows list but looks like a row, accept single row
            return [data]
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
        return []

    try:
        data = json.loads(text)
        if isinstance(data, list):
            # many JSONS dumps are arrays of store docs; decode linearly
            out_rows: List[Dict[str, Any]] = []
            for item in data:
                doc = _decode_store_like_item(item)
                if doc:
                    out_rows.extend(_extract_rows_from_store_doc(doc))
            if out_rows:
                return out_rows
        raw_rows = _normalize_loaded(data)
        if raw_rows:
            return [_flatten_json_row(r) for r in raw_rows]
        # if not normalized rows, still try store-style decoding
    except json.JSONDecodeError:
        pass

    # NDJSON or store-encoded lines
    out_rows: List[Dict[str, Any]] = []
    ndjson_items: List[Any] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        ndjson_items.append(item)
        # if plain dict, flatten
        if isinstance(item, dict):
            out_rows.append(_flatten_json_row(item))
            continue
        # store-style: top-level list containing pairs including a ["map", <pairs>]
        doc = _decode_store_like_item(item)
        if doc:
            out_rows.extend(_extract_rows_from_store_doc(doc))
    if out_rows:
        return out_rows
    # Fallback: some exporters use a JSON array across multiple lines without commas (already collected)
    if ndjson_items:
        try:
            out_rows2: List[Dict[str, Any]] = []
            for it in ndjson_items:
                doc = _decode_store_like_item(it)
                if doc:
                    out_rows2.extend(_extract_rows_from_store_doc(doc))
            if out_rows2:
                return out_rows2
        except Exception:
            pass
    # Last-resort heuristic for Action-definition lines (no entries/amounts):
    # Extract action name and synthesize dr/cr rows with branchSeq and transactionTime.
    try:
        rx_branch = re.compile(r'"branchSeq"\s*,\s*(\d+)')
        rx_time = re.compile(r'"transactionTime"\s*,\s*\[\s*"timestamp"\s*,\s*\[\s*"([^"]+)"\s*\]')
        rx_action_name = re.compile(r'\b"name"\s*,\s*"([^"]+)"')
        out_rows3: List[Dict[str, Any]] = []
        for line in text.splitlines():
            if '"Action"' not in line or '"name"' not in line:
                continue
            m_b = rx_branch.search(line)
            m_t = rx_time.search(line)
            m_a = rx_action_name.search(line)
            if not m_a:
                continue
            bseq = int(m_b.group(1)) if m_b else None
            ttime = m_t.group(1) if m_t else None
            aname = m_a.group(1)
            out_rows3.append({"branchSeq": bseq, "transactionTime": ttime, "fromDate": None, "toDate": "EndOfTime", "action": aname, "drcr": "dr"})
            out_rows3.append({"branchSeq": bseq, "transactionTime": ttime, "fromDate": None, "toDate": "EndOfTime", "action": aname, "drcr": "cr"})
        if out_rows3:
            return out_rows3
    except Exception:
        pass
    return []


def _flatten_json_row(r: Dict[str, Any]) -> Dict[str, Any]:
    """Map a possibly nested/typed JSON row to the flat field names we use in CSV.

    Target keys: branchSeq, transactionTime, fromDate, toDate, date, journalId,
    priorTxRef, selfTxRef, transactionId, reason, worker, company, country,
    action, drcr, amount, currency.
    """
    def g(obj: Dict[str, Any], *paths) -> Any:
        # return first non-None value from candidate paths (each path is tuple of keys)
        for p in paths:
            cur = obj
            ok = True
            for k in p:
                if isinstance(cur, dict) and k in cur:
                    cur = cur[k]
                else:
                    ok = False
                    break
            if ok:
                return cur
        return None

    def decode(val: Any) -> Any:
        # handle typed arrays e.g., ["timestamp", ["2025-...Z"]] or ["date", ["2025-08-19"]]
        if isinstance(val, list) and len(val) >= 2 and isinstance(val[1], list) and val[1]:
            inner = val[1][0]
            return inner
        if isinstance(val, dict):
            # common embeddings like {"timestamp": "..."} or {"date": "..."}
            for k in ("timestamp", "date", "value", "amount"):
                if k in val and isinstance(val[k], (str, int, float)):
                    return val[k]
        return val

    out: Dict[str, Any] = {}
    # direct or nested under 'data'
    out["branchSeq"] = decode(g(r, ("branchSeq",)))
    out["transactionTime"] = decode(g(r, ("transactionTime",), ("transaction", "transactionTime")))

    # validity range: prefer explicit fromDate/toDate (possibly under data); else from 'validity' temporalRange
    vf = decode(g(r, ("fromDate",), ("data", "fromDate")))
    vt = decode(g(r, ("toDate",), ("data", "toDate")))
    validity = r.get("validity")
    if (vf is None or vt is None) and isinstance(validity, list) and len(validity) >= 2:
        # e.g., ["temporalRange", [["timestamp", ["StartOfTime"]], ["timestamp", ["EndOfTime"]]]]
        rng = validity[1]
        if isinstance(rng, list) and len(rng) >= 2:
            try:
                vf = vf if vf is not None else decode(rng[0])
                vt = vt if vt is not None else decode(rng[1])
            except Exception:
                pass
    out["fromDate"] = _translate_endpoints(vf)
    out["toDate"] = _translate_endpoints(vt)

    # business date
    out["date"] = decode(g(r, ("date",), ("data", "date")))

    # identifiers and context
    out["journalId"] = decode(g(r, ("journalId",), ("data", "journalId")))
    out["priorTxRef"] = decode(g(r, ("priorTxRef",), ("transaction", "priorTxRef")))
    out["selfTxRef"] = decode(g(r, ("selfTxRef",), ("transaction", "selfTxRef")))
    out["transactionId"] = decode(g(r, ("transactionId",), ("data", "transactionId")))
    out["reason"] = decode(g(r, ("reason",), ("data", "reason")))
    out["worker"] = decode(g(r, ("worker",), ("data", "worker")))
    out["company"] = decode(g(r, ("company",), ("data", "company")))
    out["country"] = decode(g(r, ("country",), ("data", "country")))
    out["action"] = decode(g(r, ("action",), ("data", "action")))
    out["drcr"] = decode(g(r, ("drcr",), ("data", "drcr")))

    # amounts: support flat amount/currency or nested financialAmount shapes
    amount = decode(g(r, ("amount",), ("data", "amount")))
    currency = decode(g(r, ("currency",), ("data", "currency")))
    if (amount is None or currency is None):
        fa = g(r, ("financialAmount",), ("data", "financialAmount"))
        if fa is not None:
            fa_dec = decode(fa)
            if isinstance(fa_dec, dict):
                # common keys
                amount = amount if amount is not None else fa_dec.get("value") or fa_dec.get("amount") or fa_dec.get("decimalValue")
                currency = currency if currency is not None else fa_dec.get("currency") or fa_dec.get("currencyCode")
            elif isinstance(fa, list):
                # sometimes second element is dict
                try:
                    inner = fa[1][0] if isinstance(fa[1], list) and fa[1] else None
                    if isinstance(inner, dict):
                        amount = amount if amount is not None else inner.get("value") or inner.get("amount")
                        currency = currency if currency is not None else inner.get("currency") or inner.get("currencyCode")
                except Exception:
                    pass
    out["amount"] = amount
    out["currency"] = currency

    return out


def _translate_endpoints(v: Any) -> Any:
    # convert token strings to None for later normalization
    if isinstance(v, str) and v in ("EndOfTime", "StartOfTime"):
        # let StartOfTime return None; EndOfTime -> None and then later code maps to 9999-01-01
        return None
    return v


def _decode_store_like_item(item: Any) -> Dict[str, Any] | None:
    """Decode the custom typed JSONS line into a plain dict if possible.

    Looks for a pair ["map", <pairs>] and decodes recursively.
    """
    try:
        # common shape: [ [ ["opaqueId", ..], ["map", <pairs>] ], 0]
        def find_map_pair(node: Any):
            if isinstance(node, list):
                for el in node:
                    if isinstance(el, list) and len(el) == 2 and el and el[0] == "map":
                        return el[1]
                    # search deeper
                    res = find_map_pair(el)
                    if res is not None:
                        return res
            return None

        pairs_list = None
        if isinstance(item, list) and item:
            # Search whole structure, not just first element
            pairs_list = find_map_pair(item)
        if pairs_list is None:
            return None
        return _decode_typed(["map", pairs_list])
    except Exception:
        return None


def _decode_typed(node: Any) -> Any:
    """Recursively decode typed values like ["map", ...], ["elist", ...],
    ["timestamp", ["..."]], ["date", ["..."]], ["financialAmount", [...]].
    """
    # simple primitives
    if not isinstance(node, list):
        # also decode nested dict/list generically
        if isinstance(node, dict):
            return {k: _decode_typed(v) for k, v in node.items()}
        if isinstance(node, list):
            return [_decode_typed(v) for v in node]
        return node
    if len(node) == 0:
        return node
    tag = node[0]
    val = node[1] if len(node) > 1 else None

    if tag == "map":
        result: Dict[str, Any] = {}
        if isinstance(val, list):
            for kv in val:
                if isinstance(kv, list) and len(kv) == 2:
                    k, v = kv
                    key = _decode_key(k)
                    result[key] = _decode_typed(v)
        return result
    if tag == "elist":
        return [_decode_typed(v) for v in (val or [])]
    if tag in ("timestamp", "date"):
        try:
            if isinstance(val, list) and val:
                return val[0]
        except Exception:
            pass
        return val
    if tag == "opaqueId":
        try:
            if isinstance(val, list) and val:
                inner = val[0]
                # inner is a JSON string like '["accounting","JournalEntry",900]'
                py = json.loads(inner)
                return py
        except Exception:
            return val
        return val
    if tag == "financialAmount":
        try:
            mantissa = int(val[0]) if len(val) > 0 else 0
            exponent = int(val[1]) if len(val) > 1 else 0
            amount = mantissa * (10 ** exponent)
            currency = None
            if len(val) > 3 and isinstance(val[3], list) and val[3]:
                # e.g., [["ZAR"], []]
                try:
                    currency = val[3][0][0]
                except Exception:
                    currency = None
            return {"value": amount, "currency": currency}
        except Exception:
            return {"value": None, "currency": None}
    if tag == "temporalRange":
        try:
            start = _decode_typed(val[0]) if isinstance(val, list) and len(val) > 0 else None
            end = _decode_typed(val[1]) if isinstance(val, list) and len(val) > 1 else None
            return [start, end]
        except Exception:
            return val

    # fallback: decode contents
    if isinstance(val, list):
        return [_decode_typed(v) for v in val]
    return val


def _decode_key(k: Any) -> str:
    if isinstance(k, str):
        return k
    if isinstance(k, list) and k and k[0] == "opaqueId":
        try:
            py = _decode_typed(k)
            if isinstance(py, list):
                return ":".join(str(x) for x in py)
            return str(py)
        except Exception:
            return str(k)
    return str(k)


def _extract_rows_from_store_doc(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        branch_seq = doc.get("branchSeq")
        txn_time = doc.get("transactionTime")
        entries = doc.get("entries") or {}
        # entries may be a dict or a list of pairs [opaqueId, map]
        if isinstance(entries, dict):
            entry_iter = entries.items()
        elif isinstance(entries, list):
            # decode into (key, value) tuples
            tmp = []
            for el in entries:
                if isinstance(el, list) and len(el) == 2:
                    k = _decode_typed(el[0])
                    v = _decode_typed(el[1])
                    tmp.append((k, v))
            entry_iter = tmp
        else:
            entry_iter = []

        for jkey, j in entry_iter:
            if not isinstance(j, dict):
                continue
            # top-level fields on journal entry map
            vfrom = j.get("fromDate")
            vto = j.get("toDate")
            # fallback to validity if from/to not present
            if (vfrom is None or vto is None) and isinstance(j.get("validity"), list):
                try:
                    rng = j.get("validity")
                    vfrom = vfrom if vfrom is not None else (rng[0] if len(rng) > 0 else None)
                    vto = vto if vto is not None else (rng[1] if len(rng) > 1 else None)
                except Exception:
                    pass
            reason = j.get("reason")
            txid = j.get("transactionId")
            data = j.get("data") or {}
            bdate = data.get("date")
            splits = data.get("entries") or []
            # if no direct data entries, try splits[].data.entries
            if not splits and isinstance(j.get("splits"), list):
                alt_entries: List[Dict[str, Any]] = []
                alt_date = None
                for sp in j.get("splits"):
                    if isinstance(sp, dict):
                        d2 = sp.get("data") or {}
                        e2 = d2.get("entries") or []
                        if e2:
                            alt_entries.extend(e2)
                        if not bdate and d2.get("date"):
                            alt_date = d2.get("date")
                        # also derive validity if missing
                        if (vfrom is None or vto is None) and isinstance(sp.get("validity"), list):
                            try:
                                rng2 = sp.get("validity")
                                vfrom = vfrom if vfrom is not None else (rng2[0] if len(rng2) > 0 else None)
                                vto = vto if vto is not None else (rng2[1] if len(rng2) > 1 else None)
                            except Exception:
                                pass
                        # action-definition shape (no entries) => synthesize dr/cr rows by action name
                        if not e2 and (d2.get("name") or d2.get("actionName")) and (
                            d2.get("dr_path_parts") or d2.get("cr_path_parts")
                        ):
                            act_name = d2.get("name") or d2.get("actionName")
                            # create two pseudo-splits matching our downstream format
                            alt_entries.extend([
                                {"action": "dr", "usesAction": act_name, "amount": None, "annotationsUsed": {}},
                                {"action": "cr", "usesAction": act_name, "amount": None, "annotationsUsed": {}},
                            ])
                if alt_entries:
                    splits = alt_entries
                if alt_date:
                    bdate = alt_date
            # id/journalId
            jid = j.get("id") or jkey
            if isinstance(jid, list) and jid:
                # opaqueId decoded to list like ["accounting","JournalEntry",900]
                jid_str = ":".join(str(x) for x in jid)
                jid_last = jid[-1] if jid else None
            else:
                jid_str = str(jid)
                jid_last = None
            for s in splits:
                if not isinstance(s, dict):
                    continue
                drcr = s.get("action")
                uses_action = s.get("usesAction") or s.get("actionName") or s.get("action")
                amt_val = s.get("amount")
                amount = None
                currency = None
                if isinstance(amt_val, dict):
                    amount = amt_val.get("value") or amt_val.get("amount")
                    currency = amt_val.get("currency")
                else:
                    amount = amt_val
                ann = s.get("annotationsUsed") or {}
                rows.append({
                    "branchSeq": branch_seq,
                    "transactionTime": txn_time,
                    "fromDate": vfrom,
                    "toDate": vto,
                    "date": bdate,
                    "reason": reason,
                    "transactionId": txid,
                    "journalId": str(jid_last if isinstance(jid_last, (int, str)) else jid_str),
                    "worker": ann.get("worker"),
                    "company": ann.get("company"),
                    "country": ann.get("country"),
                    "action": uses_action,
                    "drcr": drcr,
                    "amount": amount,
                    "currency": currency,
                })
    except Exception:
        # if decoding fails for this doc, skip gracefully
        return []
    return rows


def _ensure_text(content: Any) -> str:
    """Return content as str regardless of bytes/str from file manager."""
    if isinstance(content, bytes):
        try:
            return content.decode("utf-8")
        except Exception:
            return content.decode("latin-1", errors="ignore")
    if isinstance(content, str):
        return content
    # file-like or other; try str()
    try:
        return str(content)
    except Exception:
        return ""


def _clean_field(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        # remove wrapping quotes and stray leading quotes
        if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
            v = v[1:-1]
        if v.startswith("'\"") and v.endswith("\""):
            v = v[2:-1]
            # handle cases like leading single quote only
            if v.startswith("'") and not v.endswith("'"):
                v = v[1:]
        # translate EndOfTime literal to a recognizable token
        if v == "EndOfTime":
            return None
    return v


def _to_text(v: Any) -> str | None:
    if v is None:
        return None
    return str(v)


def _to_int(v: Any) -> int | None:
    try:
        return int(float(v)) if v not in (None, "") else None
    except Exception:
        return None


def _to_float(v: Any) -> float | None:
    if v in (None, ""):
        return None
    try:
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        # handle accounting negatives (1,234.56) and (1234.56)
        neg = False
        if s.startswith("(") and s.endswith(")"):
            neg = True
            s = s[1:-1]
        # remove thousands separators and spaces
        s = s.replace(",", "").replace(" ", "")
        # allow leading +
        if s.startswith("+"):
            s = s[1:]
        try:
            val = float(s)
        except Exception:
            # regex fallback: first float-like number in string
            m = re.search(r"-?\d+(?:\.\d+)?", s)
            if not m:
                return None
            val = float(m.group(0))
        return -val if neg else val
    except Exception:
        return None


def _to_dt(v: Any):
    if not v:
        return None
    try:
        dt = get_datetime(v)
    except Exception:
        return None
    # Ensure naive UTC datetime for DB compatibility (no timezone suffix)
    try:
        if getattr(dt, "tzinfo", None) is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        pass
    return dt


def _to_date(v: Any):
    if not v:
        return None
    try:
        return getdate(v)
    except Exception:
        return None
