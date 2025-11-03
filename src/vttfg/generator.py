import pandas as pd, os, logging
from vttfg.config import CONFIG
logger = logging.getLogger("vttfg.generator")

def rows_to_csv_bytes(test_rows):
    cols = [
        "Document Number","Transaction Type","Message Type","Company Code","Division Code","Department Code",
        "Line Item Number","Extended Price","flexibleCodeField1","flexibleCodeField2","flexibleCodeField3","flexibleCodeField4","flexibleCodeField5",
        "Document Date","Destination Country","Destination Main Division","Destination Postal Code",
        "Phys Origin Country","Phys Origin Main Division","Phys Origin Postal Code",
        "Product Class Code","Product Code","Expected Value"
    ]
    records = []
    for r in test_rows:
        records.append({
            "Document Number": r.document_number,
            "Transaction Type": r.transaction_type,
            "Message Type": r.message_type,
            "Company Code": r.company_code,
            "Division Code": r.division_code,
            "Department Code": r.department_code,
            "Line Item Number": r.line_item_number,
            "Extended Price": r.extended_price,
            "flexibleCodeField1": r.flex1,
            "flexibleCodeField2": r.flex2,
            "flexibleCodeField3": r.flex3,
            "flexibleCodeField4": r.flex4,
            "flexibleCodeField5": r.flex5,
            "Document Date": r.document_date,
            "Destination Country": r.dest_country,
            "Destination Main Division": r.dest_main_division,
            "Destination Postal Code": r.dest_postal_code,
            "Phys Origin Country": r.phys_country,
            "Phys Origin Main Division": r.phys_main_division,
            "Phys Origin Postal Code": r.phys_postal_code,
            "Product Class Code": r.product_class_code,
            "Product Code": r.product_code,
            "Expected Value": r.expected_value
        })
    df = pd.DataFrame(records, columns=cols)
    return df.to_csv(index=False).encode("utf-8")
