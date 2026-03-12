import pandas as pd

# Sample contact data
contacts = pd.DataFrame([
    {"name": "Alice Johnson", "email": "alice@example.com", "company": "TechCorp"},
    {"name": "Bob Smith", "email": "bob@example.com", "company": "StartupXYZ"},
    {"name": "Carol White", "email": "carol@example.com", "company": "InnovateLabs"},
    {"name": "David Brown", "email": "david@example.com", "company": "DataFlow Inc"},
])

# Save to Excel
contacts.to_excel("contacts.xlsx", index=False)
print("✓ Created contacts.xlsx with 4 contacts")
print(contacts)