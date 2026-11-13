"""Item 2: DFA-based vs regex-based validation on representative inputs.   Run: python compare_dfa_regex.py"""
from dfa_engine import CODE_REGEX, LOAN_DFA, MONEY_DFA, MONEY_REGEX

CODES = ["LOANH104920", "LOANV000000", "LOANP999999", "LOANE123456", "LOANX123456", "loanh123456", "LOANH12345",
         "LOANH1234567", "LOANH12A456", "", "LOAN", " LOANH123456", "LOANHH23456"]
MONEY = ["10000", "1800000.50", "999999999", "012345", "1,50,000", "12.345", "abc", "1e6", "-5", "100.5"]


def table(title, items, dfa, rx):
    print(f"\n{title}\n{'input':<16}{'DFA':<9}{'regex':<9}{'agree':<7}final-state")
    for s in items:
        r, m = dfa.run(s), rx.fullmatch(s) is not None
        print(f"{s!r:<16}{'ACCEPT' if r['accepted'] else 'REJECT':<9}{'ACCEPT' if m else 'REJECT':<9}{str(r['accepted'] == m):<7}{r['final_state']}")


table("Application code  LOAN[HVPE][0-9]{6}", CODES, LOAN_DFA, CODE_REGEX)
table("Money field  [1-9][0-9]{0,8}(\\.[0-9]{1,2})?", MONEY, MONEY_DFA, MONEY_REGEX)
