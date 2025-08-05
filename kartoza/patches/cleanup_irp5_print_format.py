import frappe

def cleanup_irp5_print_formats():
    """Remove all IRP5 Certificate print formats"""
    
    # List of print format names to delete
    print_format_names = [
        "IRP5 Certificate",
        "IRP5/ IT3(a) Certificate", 
        "IRP5 IT3a Certificate"
    ]
    
    for name in print_format_names:
        if frappe.db.exists("Print Format", {"name": name, "doc_type": "IRP5 Certificate"}):
            try:
                frappe.delete_doc("Print Format", name, ignore_permissions=True)
                print(f"Deleted print format: {name}")
            except Exception as e:
                print(f"Error deleting {name}: {str(e)}")
    
    frappe.db.commit()
    print("IRP5 print format cleanup completed")

if __name__ == "__main__":
    cleanup_irp5_print_formats()
