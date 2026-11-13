"""Realistic valid + edge-case applications, inserted on demand via the Seed button."""
from routing_engine import URGENCY_PRIORITY, submit_report

def A(name, code, inc, amt, zone, urg="Normal", desc="", contact="9876543210"):
    return dict(reporter_name=name, reporter_contact=contact, application_code=code, income=inc, amount=amt, zone=zone, urgency=urg, description=desc)

SEED = [
    A("Suresh Kumar", "LOANH104920", "1800000", "6500000", "North", "Normal", "2BHK flat purchase in Gurugram"),
    A("Lakshmi Devi", "LOANH205511", "900000", "2200000", "South", "Normal", "Home loan for apartment in Whitefield"),
    A("Imran Qureshi", "LOANH318842", "1200000", "1800000", "South", "High", "House renovation and extension"),
    A("Nisha Patel", "LOANH402277", "1500000", "2000000", "South", "Normal", "Plot and house construction"),
    A("Ravi Teja", "LOANH550019", "2400000", "9000000", "Central", "Critical", "Property mortgage, closing deadline"),
    A("Amit Joshi", "LOANV778123", "850000", "1100000", "West", "Normal", "New car purchase"),
    A("Pooja Bansal", "LOANV123456", "2000000", "3200000", "West", "Normal", "Premium SUV vehicle loan"),
    A("Harish Gowda", "LOANV600600", "700000", "900000", "South", "Critical", "Bike for delivery business"),
    A("Divya Nair", "LOANP445566", "1100000", "400000", "East", "Normal", "Wedding expenses personal loan"),
    A("Mohan Das", "LOANP771122", "3000000", "3000000", "East", "High", "Medical and travel personal loan"),
    A("Aarav Singh", "LOANE990011", "650000", "1500000", "North", "Normal", "Masters tuition at a university"),
    A("Fatima Sheikh", "LOANE330044", "500000", "800000", "South", "Critical", "College fee due this week"),
    A("Ganesh Pillai", "LOANH884400", "1000000", "3500000", "Central", "Normal", "Home loan - car parking also needed"),
    # ---- edge cases -----------------------------------------------------------
    A("Unknown Zone Case", "LOANP220033", "800000", "300000", "Atlantis", "Normal", "Personal loan, zone not mapped"),
    A("Bad Type", "LOANX123456", "800000", "300000", "North"),
    A("Lower Case", "loanh123456", "800000", "300000", "North"),
    A("Too Short", "LOANH12345", "800000", "300000", "North"),
    A("Too Long", "LOANH1234567", "800000", "300000", "North"),
    A("Bad Income Format", "LOANV909090", "1,50,000", "300000", "West"),
    A("Income Below Bound", "LOANE808080", "9999", "300000", "West"),
    A("Bad Contact", "LOANP303030", "800000", "300000", "East", "Normal", "", "12345"),
    A("Duplicate", "LOANH104920", "1800000", "6500000", "North", "Normal", "Re-submission of an existing ID"),
]

def seed(conn):
    ordered = sorted(enumerate(SEED), key=lambda t: (URGENCY_PRIORITY.get(t[1]["urgency"], 2), t[0]))
    return [submit_report(conn, p) for _, p in ordered]
