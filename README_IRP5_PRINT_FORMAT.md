# IRP5 Certificate Print Format - Installation Summary

## What Has Been Created

I have successfully created a comprehensive print format template for the IRP5 Certificate module in Kartoza. Here's what was added:

### 1. Print Format Structure
```
/workspace/cohenix-bench/apps/kartoza/kartoza/kartoza/print_format/
├── __init__.py
└── irp5_certificate/
    ├── __init__.py
    ├── irp5_certificate.json     # Print format configuration
    └── irp5_certificate.html     # HTML template with styling
```

### 2. Installation Infrastructure
- **Patch File**: `/workspace/cohenix-bench/apps/kartoza/kartoza/patches/install_irp5_print_format.py`
- **Utility Script**: `/workspace/cohenix-bench/apps/kartoza/kartoza/kartoza/utils/install_print_format.py`
- **Patches Configuration**: Updated `/workspace/cohenix-bench/apps/kartoza/kartoza/patches.txt`
- **Fixtures Configuration**: Updated `/workspace/cohenix-bench/apps/kartoza/kartoza/hooks.py`

### 3. Documentation
- **Comprehensive Guide**: `/workspace/cohenix-bench/apps/kartoza/kartoza/docs/irp5_print_format.md`

## Installation Status
✅ **Successfully Installed** - The print format has been created and is ready to use.

## How to Access the Print Format

### Method 1: From IRP5 Certificate Form
1. Open any IRP5 Certificate document
2. Click the **"Print"** button in the toolbar
3. Select **"IRP5 Certificate"** from the format dropdown
4. The formatted certificate will open in a new tab

### Method 2: Direct Print Preview
1. Go to the IRP5 Certificate list
2. Click on any certificate
3. Use **Ctrl+P** or click the print icon
4. Select the **"IRP5 Certificate"** format

## Template Features

### Professional Layout
- Clean, SARS-compliant design
- Professional typography and spacing
- Responsive layout for screen and print
- South African tax document color scheme

### Complete Data Display
- **Certificate Information**: Number, tax year, period, dates
- **Company Details**: Name, PAYE reference, SDL reference  
- **Employee Information**: ID, name, ID number, tax number
- **Income Breakdown**: All income items with codes and descriptions
- **Deductions**: All deduction items properly categorized
- **Company Contributions**: Employer contribution details
- **Tax Summary**: PAYE, UIF, SDL, ETI calculations and totals

### Dynamic Data Integration
The template automatically pulls data from:
- IRP5 Certificate document fields
- Related Employee record (custom fields)
- Related Company record (custom fields)
- Child table records (income_details, deduction_details, company_contribution_details)

## Field Mapping

The template populates all fields from the IRP5 Certificate exactly as created in the module:

| Certificate Field | Template Display |
|-------------------|------------------|
| `certificate_number` | Certificate Number header |
| `tax_year` | Tax Year header and details |
| `employee` | Employee ID |
| `employee_name` | Employee Name |
| `company` | Company Name |
| `reconciliation_period` | Period (Interim/Final) |
| `from_date` / `to_date` | Date range |
| `income_details` | Complete income table |
| `deduction_details` | Complete deduction table |
| `company_contribution_details` | Company contributions table |
| `paye` | PAYE amount |
| `uif` | UIF amount |
| `sdl` | SDL amount |
| `eti` | ETI amount |
| `total_tax_payable` | Final total |

## Testing the Template

To test the print format:

1. **Create a sample IRP5 Certificate**:
   - Go to IRP5 Certificate > New
   - Fill in the basic details (employee, tax year, dates)
   - Click "Generate Certificate Data" to populate the child tables
   - Save the document

2. **Test the print format**:
   - Click Print > IRP5 Certificate
   - Verify all data displays correctly
   - Check formatting and styling

## Customization Options

The template is fully customizable:

### Styling Changes
Edit `/workspace/cohenix-bench/apps/kartoza/kartoza/kartoza/print_format/irp5_certificate/irp5_certificate.html`:
- Modify CSS in the `<style>` section
- Change colors, fonts, or layout
- Add company branding or logos

### Content Changes
- Add new fields from the IRP5 Certificate doctype
- Modify table structures
- Change the information layout

### Re-installation
After making changes, reinstall using:
```bash
bench execute "kartoza.patches.install_irp5_print_format.execute"
```

## Best Practices

1. **Always test changes** with sample data before production use
2. **Back up customizations** before system updates
3. **Follow Frappe conventions** for field access and formatting
4. **Use the documentation** provided in `/docs/irp5_print_format.md`

## Support

If you encounter any issues:
1. Check the installation logs: `bench logs`
2. Verify the IRP5 Certificate has data in all child tables
3. Ensure related Employee and Company records have the required custom fields
4. Review the HTML template for any syntax errors

The print format is now ready for production use and provides a professional, compliant template for IRP5 certificate generation.
