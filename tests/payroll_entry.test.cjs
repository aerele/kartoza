// Run from the bench: node --test apps/kartoza/tests/payroll_entry.test.cjs
// Execute the dialog handlers with lightweight UI doubles and the installed
// Frappe controls. No site or accounting records are modified.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const app = path.resolve(__dirname, "..");
const controls = path.resolve(app, "../frappe/frappe/public/js/frappe/form/controls");
const escape = (value) =>
	String(value ?? "")
		.replaceAll("&", "&amp;")
		.replaceAll("<", "&lt;")
		.replaceAll('"', "&quot;");

function setup() {
	let handlers, button, dialog;
	const calls = [];
	class Wrapper {
		constructor() {
			this.markup = "";
			this.rows = [];
		}
		html(value) {
			this.markup = value;
		}
		find(selector) {
			const root = this;
			if (selector.endsWith("-col")) return { remove() {} };
			if (selector === ".employee-list") {
				return {
					empty() {
						root.rows = [];
					},
					append(markup) {
						if (!root.markup.includes('<div class="row employee-list">')) return;
						const match = markup.match(/account="([^"]*)" employee="([^"]*)"/);
						if (match)
							root.rows.push({ account: match[1], employee: match[2], checked: true, markup });
					},
				};
			}
			assert.equal(selector, ".employee-checkbox:checkbox:checked");
			return {
				each(fn) {
					root.rows.filter((row) => row.checked).forEach((row, i) => fn(i, row));
				},
			};
		}
	}
	const frappe = {
		ui: {
			form: {
				Control: class {},
				on(doctype, events) {
					handlers = events;
				},
			},
		},
		utils: { escape_html: escape },
		format: (value) => value,
		render: (value) => value,
		get_doc: () => ({ default_currency: "ZAR" }),
		call: (options) => calls.push(options),
		throw: (message) => {
			throw Error(message);
		},
		set_route: (...args) => {
			frappe.route = args;
		},
	};
	const context = vm.createContext({
		frappe,
		__: (value) => value,
		$: (value) =>
			typeof value === "string"
				? dialog.fields_dict.employee_list.$wrapper.find(value)
				: value instanceof Wrapper
				? value
				: { attr: (name) => value[name] },
	});
	for (const file of ["base_input.js", "html.js"]) {
		vm.runInContext(
			fs.readFileSync(path.join(controls, file), "utf8").replace(/^import .*;\n/gm, ""),
			context
		);
	}
	frappe.ui.Dialog = class {
		constructor(options) {
			Object.assign(this, options);
			this.values = {};
			this.fields_dict = {};
			for (const df of options.fields) {
				const wrapper = new Wrapper();
				this.fields_dict[df.fieldname] = { df, $wrapper: wrapper };
				if (df.fieldtype === "HTML") {
					frappe.ui.form.ControlHTML.prototype.refresh_input.call({
						df,
						get_content: () => df.options,
						_set_html: (value) => wrapper.html(value),
					});
				} else if (df.fieldtype === "Text") {
					frappe.ui.form.ControlInput.prototype.set_disp_area.call({
						df,
						value: df.default,
						disp_area: wrapper,
					});
				}
			}
			dialog = this;
		}
		get_value(name) {
			return this.values[name];
		}
		set_value(name, value) {
			this.values[name] = value;
		}
		show() {}
		hide() {
			this.hidden = true;
		}
		change(name, value) {
			this.set_value(name, value);
			this.fields_dict[name].df.change();
		}
	};
	vm.runInContext(
		fs.readFileSync(
			process.env.PAYROLL_SCRIPT || path.join(app, "kartoza/custom_js/payroll_entry.js"),
			"utf8"
		),
		context
	);
	const employee = (id, account) => ({
		employee: id,
		employee_name: "<Name>",
		custom_payroll_payable_bank_account: account,
		custom_bank_account_currency: account === "Bank A" ? "ZAR" : "USD",
	});
	const frm = {
		doc: {
			name: "PAY-TEST",
			docstatus: 1,
			salary_slips_submitted: 1,
			company: "Test",
			employees: [
				employee("EMP-1", "Bank A"),
				employee("EMP-2", "Bank A"),
				employee("EMP-3", "Bank B"),
			],
		},
		remove_custom_button() {},
		add_custom_button(label, fn) {
			button = fn;
			return { addClass() {} };
		},
		reload_doc() {
			this.reloaded = true;
		},
	};
	// Support the old refresh handler to demonstrate the rendering regression.
	(handlers.add_bank_entry_button || handlers.refresh)(frm);
	return {
		frm,
		frappe,
		calls,
		handlers,
		open() {
			button();
			return dialog;
		},
	};
}

test("v16 renders employees, isolates dialogs, and does not duplicate on reopen", () => {
	const env = setup();
	const first = env.open();
	first.change("Bank A", 1);
	assert.deepEqual(
		first.fields_dict.employee_list.$wrapper.rows.map((row) => row.employee),
		["EMP-1", "EMP-2"]
	);
	assert.match(first.fields_dict.employee_list.$wrapper.rows[0].markup, /&lt;Name>/);
	const second = env.open();
	second.change("Bank A", 1);
	assert.equal(second.fields_dict.employee_list.$wrapper.rows.length, 2);
	second.change("Bank B", 1);
	assert.equal(second.fields_dict.employee_list.$wrapper.rows.length, 3);
	second.change("Bank A", 0);
	assert.equal(second.fields_dict.employee_list.$wrapper.rows.length, 1);
	assert.equal(first.fields_dict.employee_list.$wrapper.rows.length, 2);
});

test("selection, payment date and exchange rate reach the custom backend", () => {
	const env = setup();
	assert.equal(typeof env.handlers.add_bank_entry_button, "function");
	const d = env.open();
	assert.throws(() => d.primary_action(d.values), /Select at least one/);
	d.change("Bank A", 1);
	d.fields_dict.employee_list.$wrapper.rows[1].checked = false;
	assert.throws(() => d.primary_action(d.values), /Posting date/);
	d.change("Bank A_date", "2026-10-14");
	const rate = env.calls.pop();
	assert.equal(rate.args.to_currency, "ZAR");
	assert.equal(rate.args.transaction_date, "2026-10-14");
	rate.callback({ message: 1 });
	d.set_value("Bank A_ex_rate", -1);
	assert.throws(() => d.primary_action(d.values), /greater than zero/);
	d.set_value("Bank A_ex_rate", 1);
	d.primary_action(d.values);
	const request = env.calls.pop();
	assert.equal(request.method, "make_payment_entry");
	assert.deepEqual(JSON.parse(JSON.stringify(request.doc.selected_payment_account)), {
		"Bank A": {
			employees: ["EMP-1"],
			currency: "ZAR",
			posting_date: "2026-10-14",
			exchange_rate: 1,
		},
	});
	assert.equal(d.hidden, undefined);
	request.callback({ exc: "Failure" });
	assert.equal(d.hidden, undefined);
	assert.equal(env.frm.reloaded, undefined);
	request.callback({});
	assert.equal(d.hidden, true);
	assert.equal(env.frm.reloaded, true);
	assert.equal(env.frappe.route[1], "Journal Entry");
});

test("foreign-currency accounts and existing payment flags retain their controls", () => {
	const env = setup();
	env.frm.doc.employees[0].custom_is_bank_entry_creaeted = 1;
	env.frm.doc.employees[0].custom_is_company_contribution_created = 1;
	env.frm.doc.employees[1].custom_is_bank_entry_creaeted = 1;
	env.frm.doc.employees[1].custom_is_company_contribution_created = 1;
	const d = env.open();
	assert.equal(d.fields_dict["Bank A"].df.read_only, 1);
	assert.equal(d.fields_dict["Bank B"].df.read_only, 0);
	assert.equal(d.fields_dict["Bank B_ex_rate"].df.read_only, 0);
	d.change("Bank B", 1);
	d.change("Bank B_date", "2026-10-15");
	const rate = env.calls.pop();
	assert.equal(rate.args.from_currency, "USD");
	rate.callback({ message: 17.25 });
	d.primary_action(d.values);
	assert.equal(env.calls[0].doc.selected_payment_account["Bank B"].exchange_rate, 17.25);
	assert.equal(env.calls[0].doc.selected_payment_account["Bank B"].currency, "USD");
});
