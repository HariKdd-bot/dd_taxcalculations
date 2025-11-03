def validate_uc3(extraction):
    questions = []
    if not extraction.get("item_codes") and not extraction.get("product_classes"):
        questions.append("No product codes or classes found. Provide at least one.")
    if not extraction.get("states") and not extraction.get("postal_codes"):
        questions.append("No jurisdictions found (states or postal_codes). Confirm scope.")
    if not extraction.get("date_specs"):
        questions.append("No effective date provided. Will use JIRA creation date; confirm.")
    return questions
