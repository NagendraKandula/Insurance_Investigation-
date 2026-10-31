from detection.db_loader import DatabaseLoader
from detection.graph_builder import GraphBuilder
from detection.duplicate_invoice_detector import DuplicateInvoiceDetector

# Load database
loader = DatabaseLoader()
data = loader.load_all_data()

# Build graph
builder = GraphBuilder()
graph = builder.build(data)

# Run detector
detector = DuplicateInvoiceDetector(graph)

findings = detector.detect()

print("\n========== DUPLICATE INVOICE RESULTS ==========")

for finding in findings:

    evidence = finding["evidence"]

    print("\nInvoice Number:", evidence["invoice_number"])
    print("Invoice Count:", evidence["invoice_count"])
    print("Distinct Claimants:", evidence["distinct_claimant_count"])
    print("Claimants:", evidence["claimant_ids"])

    for invoice in evidence["invoices"]:
        print(
            f"  Invoice: {invoice['invoice_id']} | "
            f"Provider: {invoice['provider_id']} | "
            f"Claim: {invoice['claim_id']} | "
            f"Claimant: {invoice['claimant_id']} | "
            f"Amount: {invoice['invoice_amount']}"
        )

print("\nTotal duplicate invoice findings:", len(findings))