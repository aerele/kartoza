frappe.ui.form.on('Bitemporal Analysis', {
  refresh: function(frm) {
    // default to first tab (Import)
    if (frm.tabs && frm.tabs.tabs_label && frm.tabs.tabs_label.length) {
      frm.tabs.set_active(frm.tabs.tabs_label[0]);
    }
    render_import(frm);
    render_timeline(frm);

  // no text live bindings needed now; remaining filters use change handlers
  },
  import_ref: function(frm) {
    render_import(frm);
    render_timeline(frm);
  },
  view_mode: function(frm) {
    render_timeline(frm);
  },
  timeline_mode: function(frm) {
    render_timeline(frm);
  },
  axis_orientation: function(frm) {
    render_timeline(frm);
  },
  filter_action: function(frm) {
    render_timeline_debounced(frm);
  },
  filter_from: function(frm) {
    render_timeline_debounced(frm);
  },
  filter_to: function(frm) {
    render_timeline_debounced(frm);
  }
});

function render_import(frm) {
  const name = frm.doc.import_ref;
  const $w = frm.get_field('import_embed').$wrapper;
  const listRoute = '/app/bitemporal-import';
  const formRoute = name ? `/app/bitemporal-import/${encodeURIComponent(name)}` : null;
  const html = `
    <div class="d-flex gap-2">
      <button class="btn btn-primary" data-action="open-list">Open Bitemporal Import (List)</button>
      ${formRoute ? `<a class="btn btn-secondary" href="${formRoute}">Open Selected: ${frappe.utils.escape_html(name)}</a>` : ''}
    </div>
    <div class="text-muted small mt-2">This opens the actual Import page instead of embedding it here.</div>
  `;
  $w.html(html);
  $w.find('[data-action="open-list"]').on('click', () => frappe.set_route(listRoute));
  // Fill Details tab content (not under Import)
  const $d = frm.get_field('details_html')?.$wrapper;
  if ($d && !$d.data('bi-details-set')) {
    $d.html(`
        <style>
          .bi-details h4 { margin: 8px 0 6px; }
          .bi-details p { margin: 0 0 8px; color: #374151; }
          .bi-details code { background: #f3f4f6; padding: 0 4px; border-radius: 3px; }
          .bi-details ul { margin: 4px 0 10px 18px; }
          .bi-details li { margin: 4px 0; }
          .bi-muted { color: #6b7280; }
        </style>
        <div class="bi-details">
          <h4>Bitemporal data in this UI</h4>
          <p>
            This analysis treats every record with two time axes: <b>transaction-time</b> (when the change was committed)
            and <b>valid-time</b> (when the fact is true in the business world). The timeline view plots
            <b>X = valid-time</b> (from <code>fromDate</code> to <code>toDate</code>) and <b>Y = transaction-time</b>
            (from a transaction’s <code>transactionTime</code> until it is superseded by a later transaction on the same branch).
          </p>

          <h4>Transaction-time (when a change was committed)</h4>
          <ul>
            <li>At the top of each transaction block: <code>"transactionTime": ["timestamp", ["2025-08-19T08:26:07.850148311Z"]]</code></li>
            <li>Also identified by <code>"branch": "branchMain"</code> and <code>"branchSeq": N</code> (sequence of commits)</li>
          </ul>

          <h4>Valid-time (business/effective time)</h4>
          <ul>
            <li>For most entities: <code>"validity": ["temporalRange", [["timestamp", ["StartOfTime"]], ["timestamp", ["EndOfTime"]]]]</code></li>
            <li>For entries: <code>data.fromDate</code> and <code>data.toDate</code> (often <code>StartOfTime/EndOfTime</code> for definitions)</li>
            <li>For journal postings: <code>"data": { "date": ["date", ["2025-08-19"]] }</code> plus a validity window on the entry itself
                (e.g., a preliminary record closed at <code>2025-08-19T00:00:00Z</code>, then a new record opens from the new commit time)</li>
          </ul>
          <p class="bi-muted">Note: In this UI, open-ended <code>toDate</code>/<code>EndOfTime</code> is represented as <code>9999-01-01</code>.</p>

          <h4>transaction-time axis (when the fact was recorded)</h4>
          <ul>
            <li><b>transactionTime</b>: The exact timestamp the transaction was committed to the store (transaction time).</li>
            <li><b>branchSeq</b>: Monotonic sequence number on the branch for this transaction.</li>
            <li><b>branch</b>: Name of the branch the transaction was committed to (e.g., <code>branchMain</code>).</li>
            <li><b>priorTxRef</b>: Opaque reference to the previous transaction in the branch (lineage).</li>
            <li><b>selfTxRef</b>: Opaque reference to this transaction (lineage anchor for joins and audits).</li>
          </ul>

          <h4>valid-time axis (when the fact is true in the business world)</h4>
          <ul>
            <li><b>date</b>: Business date on the journal entry (valid-from for the business).</li>
            <li><b>fromDate</b>: Validity window start (usually equals the journal’s business date or the split’s validity start).</li>
            <li><b>toDate</b>: Validity window end (<code>EndOfTime</code> / <code>9999-01-01</code> indicates the record is currently valid).</li>
            <li class="bi-muted">Tip (derived): <code>isCurrent = (toDate == 'EndOfTime' || toDate == '9999-01-01')</code></li>
          </ul>

          <h4>identity and linkage</h4>
          <ul>
            <li><b>journalId</b>: Stable journal entry identifier (stringified opaque id from JSON).</li>
            <li><b>transactionId</b>: Journal entry’s numeric id within the payload (convenient for grouping all lines of a JE).</li>
          </ul>

          <h4>business context (not temporal, but needed in UI)</h4>
          <ul>
            <li><b>reason</b>: Narrative for the journal (e.g., Post earnings, Post tax withholdings).</li>
            <li><b>worker</b>: Worker annotation on the line (who).</li>
            <li><b>company</b>: Company annotation on the line (which entity).</li>
            <li><b>country</b>: Country annotation on the line (jurisdiction).</li>
            <li><b>action</b>: Accounting action/bucket used for posting (e.g., salary, tax).</li>
            <li><b>drcr</b>: Debit or credit side of the line.</li>
            <li><b>amount</b>: Monetary amount (scaled from financialAmount; decimal preserved).</li>
            <li><b>currency</b>: Currency code from financialAmount (e.g., ZAR).</li>
          </ul>
          <p class="bi-muted">Use the View toggle (Table / Timeline) and filters to explore both temporal dimensions clearly.</p>
        </div>
      `).data('bi-details-set', true);
  }
}

function render_timeline(frm) {
  const name = frm.doc.import_ref;
  if (!name) {
    frm.get_field('timeline_view').$wrapper.empty();
    return;
  }
  frappe.call({
    method: 'kartoza.kartoza.doctype.bitemporal_analysis.bitemporal_analysis.get_import_rows',
    args: { import_name: name }
  }).then(r => {
    let rows = r.message.rows || [];
    // apply filters
    const f = frm.doc;
    if (f.filter_action) rows = rows.filter(x => (x.action || '').toLowerCase() === f.filter_action.toLowerCase());
  // worker and company filters removed per requirements
    if (f.filter_from) rows = rows.filter(x => cmp_dt(x.transaction_time, f.filter_from) >= 0);
    if (f.filter_to) rows = rows.filter(x => cmp_dt(x.transaction_time, f.filter_to) <= 0);

    // group by transaction_time then branch_seq
    rows.sort((a,b) => cmp_dt(a.transaction_time, b.transaction_time) || (a.branch_seq||0)-(b.branch_seq||0));
    const groups = [];
    let curKey = null, cur = null;
    for (const r2 of rows) {
      const key = `${fmt_dt(r2.transaction_time)}|${r2.branch_seq||''}`;
      if (key !== curKey) {
        curKey = key; cur = { key, rows: [] }; groups.push(cur);
      }
      cur.rows.push(r2);
    }
    // render full-width
    const $target = frm.get_field('timeline_view').$wrapper;
  const mode = (frm.doc.view_mode || 'Table').toLowerCase();
    $target.empty();
  if (!groups.length) {
      $target.html('<div class="text-muted">No rows match filters.</div>');
      return;
    }
    const containerStart = `
      <style>
        .ba-section { margin-top: 12px; }
        .ba-header { font-weight: 600; margin-bottom: 6px; }
        .ba-table .table { width: 100%; }
        .ba-timeline { border-left: 2px solid #e5e7eb; padding-left: 8px; }
        .ba-band { position: relative; height: 28px; margin: 8px 0; background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 4px; }
        .ba-bar { position: absolute; top: 2px; height: 22px; background: #4f46e5; border-radius: 3px; color: #fff; font-size: 11px; line-height: 22px; padding: 0 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .ba-legend { font-size: 12px; color: #6b7280; }
      </style>`;
    const parts = [containerStart];
    if (mode === 'table') {
      for (const g of groups) {
        const [ts, bseq] = g.key.split('|');
        parts.push(`<div class="ba-section">
          <div class="ba-header">Transaction: ${ts} · Branch ${frappe.utils.escape_html(bseq)}</div>
          <div class="ba-table">${render_table(
            ['Valid From','Valid To','Date','Reason','Action','Dr/Cr','Amount','Cur'],
            g.rows.map(x => [fmt_dt(x.valid_from), fmt_dt(x.valid_to || '9999-01-01 00:00:00'), fmt_d(x.date), esc(x.reason), esc(x.action), esc(x.drcr||''), fmt_amt(x.amount), esc(x.currency||'')])
          )}</div>
        </div>`);
      }
    } else {
      // Timeline renderings
  // Map user-facing labels to internal modes
  const tl_raw = frm.doc.timeline_mode || '';
  let tmode = 'bands';
  if (tl_raw.startsWith('Transaction-time')) tmode = 'lifespan';
  if (tl_raw.startsWith('Valid-time')) tmode = 'bands';
  if (tl_raw.startsWith('Both')) tmode = 'both';
      const palette = ['#2563eb','#059669','#f59e0b','#ec4899','#10b981','#8b5cf6','#ef4444','#14b8a6'];
      const colorFor = (s) => palette[Math.abs(hashCode((s||'').toLowerCase())) % palette.length];

      // Effective time range across all rows
      const effValsAll = rows.map(x => ({ from: toDate(x.valid_from), to: toDate(x.valid_to || '9999-01-01 00:00:00') })).filter(v => v.from || v.to);
      if (!effValsAll.length) { $target.html('<div class="text-muted">No valid periods to plot.</div>'); return; }
      const effMin = new Date(Math.min(...effValsAll.map(v => (v.from||v.to).getTime())));
      const naturals = effValsAll.map(v => v.to).filter(d => d && d.getFullYear() < 2200);
      const effMax = naturals.length ? new Date(Math.max(...naturals.map(d => d.getTime()))) : new Date(Math.max(...effValsAll.map(v => (v.to||v.from).getTime())));
      const xSpan = Math.max(1, effMax - effMin);
      const W = 1000, margin = {l: 160, r: 20, t: 20, b: 40};
      const plotW = W - margin.l - margin.r;
      const xScale = (d) => margin.l + (Math.max(effMin, Math.min(effMax, d)) - effMin) / xSpan * plotW;

      if (tmode === 'bands') {
        // group by pure transaction_time label
        const tmap = new Map();
        for (const r4 of rows) {
          const d = toDate(r4.transaction_time);
          const key = d ? frappe.datetime.str_to_user(frappe.datetime.obj_to_str(d)) : (r4.transaction_time||'-');
          (tmap.get(key) || tmap.set(key, []).get(key)).push(r4);
        }
        const bands = Array.from(tmap.entries()).map(([k, arr]) => ({ key:k, rows: arr }));
        // sort bands by actual date
        bands.sort((a,b) => cmp_dt(a.rows[0]?.transaction_time, b.rows[0]?.transaction_time));
        const trackH = 20, trackGap = 10;
        // Infinity handling: if any valid_to is open-ended, extend x-domain and draw a dashed marker
        const hasOpen = rows.some(x => {
          const vt = toDate(x.valid_to || '9999-01-01 00:00:00');
          return vt && vt.getFullYear && vt.getFullYear() >= 2200;
        });
        const padMs = 1000 * 60 * 60 * 24 * 30; // 30 days
        const naturalsAll = rows
          .map(x => toDate(x.valid_to || '9999-01-01 00:00:00'))
          .filter(d => d && d.getFullYear && d.getFullYear() < 2200);
        const effMaxVis = naturalsAll.length ? new Date(Math.max(...naturalsAll.map(d => d.getTime())) + (hasOpen ? padMs : 0)) : new Date(effMax.getTime() + padMs);
        const xScaleVis = (d) => margin.l + (Math.max(effMin, Math.min(effMaxVis, d)) - effMin) / (effMaxVis - effMin) * plotW;
        let y = margin.t;
        const svg = [];
        for (const band of bands) {
          svg.push(`<text x="${margin.l-8}" y="${y + 12}" text-anchor="end" font-size="12" fill="#374151">${frappe.utils.escape_html(band.key)}</text>`);
          let idx = 0;
          for (const r5 of band.rows) {
            const vf = toDate(r5.valid_from) || effMin;
            const vt0 = toDate(r5.valid_to || '9999-01-01 00:00:00') || effMaxVis;
            const vt = (vt0.getFullYear && vt0.getFullYear() >= 2200) ? effMaxVis : vt0;
            const y0 = y + idx * (trackH + trackGap);
            const fillEff = colorFor(r5.action || r5.drcr || '');
            const label = `${(r5.action||'').trim()} ${fmt_amt(r5.amount)} ${(r5.currency||'').trim()}`.trim();
            // Effective interval (dark)
            let x0 = xScaleVis(vf), x1 = xScaleVis(vt);
            let w = Math.max(2, x1 - x0);
            svg.push(`<rect x="${x0}" y="${y0}" width="${w}" height="${trackH-6}" fill="${fillEff}" opacity="0.9" rx="3" ry="3">
              <title>${frappe.utils.escape_html(`${band.key} | Effective: ${label} | Eff: ${fmt_dt(r5.valid_from)} → ${fmt_dt(r5.valid_to)}`)}</title>
            </rect>`);
            // Asserted interval (light), starts at max(valid_from, transaction_time)
            const atStart = toDate(r5.transaction_time) || vf;
            const ax0 = xScaleVis(atStart > vf ? atStart : vf);
            const ax1 = x1;
            const aw = Math.max(1, ax1 - ax0);
            svg.push(`<rect x="${ax0}" y="${y0 + (trackH-6) - 6}" width="${aw}" height="6" fill="#9CA3AF" opacity="0.8" rx="3" ry="3">
              <title>${frappe.utils.escape_html(`${band.key} | Asserted: ${label} | From txn ${fmt_dt(r5.transaction_time)} → ${fmt_dt(r5.valid_to)}`)}</title>
            </rect>`);
            if (w > 120) svg.push(`<text x="${x0+4}" y="${y0+12}" font-size="11" fill="#ffffff">${frappe.utils.escape_html(label)}</text>`);
            idx++;
          }
          y += Math.max(trackH, band.rows.length*(trackH+trackGap)) + 16;
        }
        const H = y + margin.b;
        // X axis (effective time)
        svg.push(`<line x1="${margin.l}" y1="${H-margin.b}" x2="${W-margin.r}" y2="${H-margin.b}" stroke="#e5e7eb" stroke-width="2" />`);
        const xt = [effMin, new Date(effMin.getTime()+ (effMaxVis - effMin)/2), effMaxVis];
        for (const t of xt) {
          const x = xScaleVis(t);
          svg.push(`<line x1="${x}" y1="${H-margin.b}" x2="${x}" y2="${H-margin.b+6}" stroke="#9ca3af" />`);
          const lbl = (hasOpen && t.getTime() === effMaxVis.getTime()) ? 'Infinity' : frappe.utils.escape_html(frappe.datetime.str_to_user(frappe.datetime.obj_to_str(t)));
          svg.push(`<text x="${x}" y="${H-margin.b+20}" text-anchor="middle" font-size="12" fill="#6b7280">${lbl}</text>`);
        }
        // Infinity marker
        if (hasOpen) {
          const xInf = xScaleVis(effMaxVis);
          svg.push(`<line x1="${xInf}" y1="${margin.t-4}" x2="${xInf}" y2="${H-margin.b}" stroke="#9ca3af" stroke-width="2" stroke-dasharray="4,4" />`);
        }
        const svgWrap = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMinYMin meet" style="width:100%;height:auto">${svg.join('')}</svg>`;
        parts.push(`<div class="ba-section">${svgWrap}<div class="ba-legend">X: Effective Time, bands grouped by Transaction Time</div></div>`);
      } else if (tmode === 'lifespan' || tmode === 'both') {
        // Lifespan mode: rectangles spanning until next txn in branch
        // Transaction time range across all rows
        const txnTimes = rows.map(x => toDate(x.transaction_time)).filter(Boolean);
        if (!txnTimes.length) { $target.html('<div class="text-muted">No transaction times to plot.</div>'); return; }
  const txnMin = new Date(Math.min(...txnTimes.map(d => d.getTime())));
  const txnMax = new Date(Math.max(...txnTimes.map(d => d.getTime())));
  // Apply filter-specified domain if provided
  const ffrom = frm.doc.filter_from ? toDate(frm.doc.filter_from) : null;
  const fto = frm.doc.filter_to ? toDate(frm.doc.filter_to) : null;
  const txMinD = ffrom && !isNaN(ffrom) ? ffrom : txnMin;
  const txMaxD = fto && !isNaN(fto) ? fto : txnMax;
  // Effective time domain with Infinity handling
  const hasOpen2 = rows.some(x => { const vt = toDate(x.valid_to || '9999-01-01 00:00:00'); return vt && vt.getFullYear && vt.getFullYear() >= 2200; });
  const padMs2 = 1000*60*60*24*30;
  const naturals2 = rows.map(x => toDate(x.valid_to || '9999-01-01 00:00:00')).filter(d => d && d.getFullYear && d.getFullYear()<2200);
  const effMaxVis2 = naturals2.length ? new Date(Math.max(...naturals2.map(d=>d.getTime())) + (hasOpen2?padMs2:0)) : new Date(effMax.getTime()+padMs2);
        // Map each transaction time to the next global transaction time
        const sortedTxn = Array.from(new Set(txnTimes.map(d => d.getTime()))).sort((a,b)=>a-b).map(t=>new Date(t));
        const nextTxnMap = new Map();
        for (let i=0;i<sortedTxn.length;i++){ nextTxnMap.set(sortedTxn[i].getTime(), i<sortedTxn.length-1 ? sortedTxn[i+1] : txnMax); }
  const ySpan = Math.max(1, txMaxD - txMinD);
        const byBranch = new Map();
        for (const r2 of rows) {
          const key = String(r2.branch_seq || '—');
          (byBranch.get(key) || byBranch.set(key, []).get(key)).push(r2);
        }
  const H = 620;
        const axisSwap = (frm.doc.axis_orientation||'').startsWith('Transaction X');
        const xScale2 = axisSwap
          ? (d) => margin.l + ((Math.max(txMinD, Math.min(txMaxD, d)) - txMinD) / ySpan * plotW)
          : (d) => margin.l + ((Math.max(effMin, Math.min(effMaxVis2, d)) - effMin) / (effMaxVis2 - effMin) * plotW);
        // Invert Y so earliest date is at the top (smaller date -> smaller y)
        const yScale = axisSwap
          ? (d) => margin.t + ((Math.max(effMin, Math.min(effMaxVis2, d)) - effMin) / (effMaxVis2 - effMin) * (H - margin.t - margin.b))
          : (d) => margin.t + ((Math.max(txMinD, Math.min(txMaxD, d)) - txMinD) / ySpan * (H - margin.t - margin.b));
        const svg = [];
        // Axes (swap-aware)
  const xticks = axisSwap ? [txMinD, new Date(txMinD.getTime()+ySpan/2), txMaxD] : [effMin, new Date(effMin.getTime()+ (effMaxVis2-effMin)/2), effMaxVis2];
  const yticks = axisSwap ? [effMin, new Date(effMin.getTime()+ (effMaxVis2-effMin)/2), effMaxVis2] : [txMinD, new Date(txMinD.getTime()+ySpan/2), txMaxD];
        svg.push(`<line x1="${margin.l}" y1="${H-margin.b}" x2="${W-margin.r}" y2="${H-margin.b}" stroke="#e5e7eb" stroke-width="2" />`);
        for (const t of xticks) {
          const x = xScale2(t);
          svg.push(`<line x1="${x}" y1="${H-margin.b}" x2="${x}" y2="${H-margin.b+6}" stroke="#9ca3af" />`);
          const lbl = (!axisSwap && hasOpen2 && t.getTime() === effMaxVis2.getTime()) ? 'Infinity' : frappe.utils.escape_html(frappe.datetime.str_to_user(frappe.datetime.obj_to_str(t)));
          svg.push(`<text x="${x}" y="${H-margin.b+20}" text-anchor="middle" font-size="12" fill="#6b7280">${lbl}</text>`);
        }
        svg.push(`<line x1="${margin.l}" y1="${margin.t}" x2="${margin.l}" y2="${H-margin.b}" stroke="#e5e7eb" stroke-width="2" />`);
        for (const t of yticks) {
          const yv = yScale(t);
          svg.push(`<line x1="${margin.l-6}" y1="${yv}" x2="${margin.l}" y2="${yv}" stroke="#9ca3af" />`);
          svg.push(`<text x="${margin.l-10}" y="${yv+4}" text-anchor="end" font-size="12" fill="#6b7280">${frappe.utils.escape_html(frappe.datetime.str_to_user(frappe.datetime.obj_to_str(t)))}</text>`);
        }
        for (const [bkey, arr] of byBranch.entries()) {
          const sorted = arr.slice().sort((a,b) => cmp_dt(a.transaction_time, b.transaction_time));
          for (let i=0; i<sorted.length; i++) {
            const r3 = sorted[i];
            const t0 = toDate(r3.transaction_time) || txnMin;
            const t1 = nextTxnMap.get((t0||txnMin).getTime()) || txnMax;
            let vf = toDate(r3.valid_from) || effMin;
            let vt = toDate(r3.valid_to || '9999-01-01 00:00:00') || effMaxVis2;
            if (vt.getFullYear && vt.getFullYear() >= 2200) vt = effMaxVis2;
            const x0 = xScale2(axisSwap ? t0 : vf), x1 = xScale2(axisSwap ? t1 : vt);
            const y0 = yScale(axisSwap ? vf : t0), y1 = yScale(axisSwap ? vt : t1);
            const w = Math.max(2, x1 - x0);
            const h = Math.max(4, Math.abs(y1 - y0));
            const fill = colorFor(r3.action || r3.drcr || '');
            const label = `${(r3.action||'').trim()} ${fmt_amt(r3.amount)} ${(r3.currency||'').trim()}`.trim();
            const ry = Math.min(y0, y1);
            svg.push(`<rect x="${x0}" y="${ry}" width="${w}" height="${h}" fill="${fill}" opacity="0.85" rx="3" ry="3">
              <title>${frappe.utils.escape_html(`Branch ${bkey} | ${label}\nTxn: ${fmt_dt(r3.transaction_time)} → ${frappe.datetime.str_to_user(frappe.datetime.obj_to_str(t1))}\nEff: ${fmt_dt(r3.valid_from)} → ${fmt_dt(r3.valid_to)}`)}</title>
            </rect>`);
            if (w > 100 && h > 14) {
              svg.push(`<text x="${x0+4}" y="${ry+14}" font-size="11" fill="#ffffff">${frappe.utils.escape_html(label)}</text>`);
            }
          }
        }
        // Infinity marker for effective X
        if (!axisSwap && hasOpen2) {
          const xInf = xScale2(effMaxVis2);
          svg.push(`<line x1="${xInf}" y1="${margin.t-4}" x2="${xInf}" y2="${H-margin.b}" stroke="#9ca3af" stroke-width="2" stroke-dasharray="4,4" />`);
        }
  const svgWrap = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMinYMin meet" style="width:100%;height:auto">${svg.join('')}</svg>`;
  parts.push(`<div class="ba-section">${svgWrap}<div class="ba-legend">X: Effective Time (Valid From→To), Y: Transaction Time (from txn to next)</div></div>`);
      }
    }
    $target.html(parts.join('\n'));
  });
}

function render_timeline_debounced(frm) {
  if (frm._ba_timer) clearTimeout(frm._ba_timer);
  frm._ba_timer = setTimeout(() => render_timeline(frm), 200);
}

// details moved inline under Import as helper text below the embed

function summarize(rows){
  const acc = { action:{}, worker:{}, company:{} };
  for (const r of rows){
    const a=(r.action||'').toLowerCase(); if (a) acc.action[a]=(acc.action[a]||0)+1;
    const w=(r.worker||'').toLowerCase(); if (w) acc.worker[w]=(acc.worker[w]||0)+1;
    const c=(r.company||'').toLowerCase(); if (c) acc.company[c]=(acc.company[c]||0)+1;
  }
  return acc;
}

function render_table(head, body) {
  const th = head.map(h => `<th>${frappe.utils.escape_html(h)}</th>`).join('');
  const trs = body.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join('')}</tr>`).join('');
  return `<div class="table-responsive"><table class="table table-sm table-bordered w-100">${th?`<thead><tr>${th}</tr></thead>`:''}<tbody>${trs}</tbody></table></div>`;
}

function fmt_dt(v) { if (!v) return ''; return frappe.datetime.str_to_user(frappe.datetime.obj_to_str(v)); }
function fmt_d(v) { if (!v) return ''; return frappe.datetime.str_to_user(frappe.datetime.obj_to_str(v)); }
function fmt_amt(v) { if (v==null) return ''; try { return format_currency(v); } catch(e){ return String(v); } }
function esc(s){ return frappe.utils.escape_html(s||''); }
function cmp_dt(a, b) {
  const sa = a ? frappe.datetime.str_to_obj(a) || new Date(a) : null;
  const sb = b ? frappe.datetime.str_to_obj(b) || new Date(b) : null;
  if (!sa && !sb) return 0; if (!sa) return -1; if (!sb) return 1;
  return sa - sb;
}

function toDate(v){
  if (!v) return null;
  try { return frappe.datetime.str_to_obj(v); } catch(e) {}
  const d = new Date(v); return isNaN(d) ? null : d;
}

function hashCode(str){
  let h = 0; for (let i=0;i<str.length;i++){ h = ((h<<5)-h) + str.charCodeAt(i); h|=0; } return h;
}
