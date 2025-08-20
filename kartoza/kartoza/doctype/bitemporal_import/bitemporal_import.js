frappe.ui.form.on('Bitemporal Import', {
  refresh: function(frm) {
    frm.add_custom_button('Parse Now', () => trigger_parse(frm));
    frm.add_custom_button('Load Example', () => trigger_example(frm));
  render_preview(frm);
  },
  parse_btn: function(frm) { trigger_parse(frm); },
  load_example_btn: function(frm) { trigger_example(frm); }
});

function trigger_parse(frm) {
  if (!frm.doc.upload) {
    frappe.msgprint('Attach a file first.');
    return;
  }
  frappe.call({
    method: 'kartoza.kartoza.doctype.bitemporal_import.bitemporal_import.parse_file',
  args: { docname: frm.doc.name, file_url: frm.doc.upload, input_type: frm.doc.input_type },
    freeze: true,
    freeze_message: 'Parsing file...'
  }).then(r => {
    try {
      const n = (r && r.message && r.message.rows) || 0;
      frappe.show_alert({message: `Parsed ${n} rows`, indicator: n > 0 ? 'green' : 'orange'});
    } catch(e) {}
    frm.reload_doc();
  }).catch(err => {
    frappe.msgprint(__('Parse failed: {0}', [err && err.message || err]));
  });
}

function trigger_example(frm) {
  frappe.call({
    method: 'kartoza.kartoza.doctype.bitemporal_import.bitemporal_import.load_example',
    args: { docname: frm.doc.name },
    freeze: true,
    freeze_message: 'Loading example...'
  }).then(() => frm.reload_doc());
}

function render_preview(frm) {
  const wrapper = frm.fields_dict.preview_html?.$wrapper;
  if (!wrapper) return;
  const rows = (frm.doc.rows || []).slice().sort((a,b) => {
    // sort by transaction_time then branch_seq then journal/transaction
    const ta = (a.transaction_time || '') + '';
    const tb = (b.transaction_time || '') + '';
    if (ta < tb) return -1; if (ta > tb) return 1;
    return (a.branch_seq || 0) - (b.branch_seq || 0);
  });
  if (!rows.length) {
    wrapper.html('<div class="text-muted">No rows yet. Parse a file to preview.</div>');
    return;
  }

  // group by branch_seq and transaction_time
  const groups = {};
  rows.forEach(r => {
    const key = `${r.branch_seq || ''}|${r.transaction_time || ''}`;
    (groups[key] = groups[key] || []).push(r);
  });

  const html = Object.entries(groups).map(([key, arr]) => {
    const [branchSeq, txTime] = key.split('|');
    const header = `<div class="h6" style="margin-top:8px">Tx Time: ${txTime || '-'} · Branch Seq: ${branchSeq || '-'}</div>`;
    const tableHead = `<table class="table table-bordered small" style="margin-bottom:12px">
      <thead><tr>
        <th>Date</th><th>Valid From</th><th>Valid To</th><th>Reason</th><th>Action</th><th>Dr/Cr</th><th class="text-right">Amount</th><th>Currency</th>
      </tr></thead><tbody>`;
    const body = arr.map(r => `<tr>
      <td>${r.date || ''}</td>
      <td>${r.valid_from || ''}</td>
      <td>${r.valid_to || ''}</td>
      <td>${frappe.utils.escape_html(r.reason || '')}</td>
      <td>${frappe.utils.escape_html(r.action || '')}</td>
      <td>${r.drcr || ''}</td>
      <td class="text-right">${format_currency(r.amount || 0, r.currency || frm.doc.company_currency || 'ZAR')}</td>
      <td>${r.currency || ''}</td>
    </tr>`).join('');
    return header + tableHead + body + '</tbody></table>';
  }).join('');
  wrapper.html(html);
}
