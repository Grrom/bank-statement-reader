from io import BytesIO
import os
import requests
import pdfplumber

class JournalEntry:
    def __init__(self, date, details, credit, debit, running_balance):
        self.date = date
        self.details = details
        self.credit = credit
        self.debit = debit
        self.running_balance = running_balance

    def __str__(self):
        return f"Date: {self.date}\nDetails: {self.details}\nCredit: {self.credit}\nDebit: {self.debit}\nRunning Balance: {self.running_balance}\n"


def process_bank_statement(request):
    """Responds to any HTTP request.
        Args:
            request (flask.Request): HTTP request object.
        Returns:
            The response text or any set of values that can be turned into a
            Response object using
            `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
        """
    request_json = request.get_json()

    file = request_json.get("file")
    journal_entries = get_journal_entries(file)
    for entry in journal_entries:
        print(entry)

    return f'Hello World!'


def get_journal_entries(file_url):
    entries_to_ignore = [
        "Inbound interbank transfer",
        "Transfer to Go Save account",
        "Transfer from Go Save account",
    ]
    response = requests.get(file_url)
    statement_pdf = BytesIO(response.content)
    
    journal_entries = []
    with pdfplumber.open(statement_pdf, password = os.getenv("GOTYME_BS_PASSWORD")) as pdf:
        for page in pdf.pages:
            is_in_table = False
            for line in page.extract_text().split('\n'):
                if not is_in_table:
                    if line == "Date Details Credits Debits Running Balance":
                        is_in_table = True
                        continue
                    continue
                if is_in_table and line == "All figures are in PHP.":
                    break

                line_split = line.split()
                details = " ".join(line_split[1:-3])

                if details in entries_to_ignore:
                    continue

                date = line_split[0]
                running_balance = line_split[-1]
                debits = line_split[-2]
                credits = line_split[-3]

                entry = JournalEntry(
                    date=date,
                    details=details,
                    credit=credits,
                    debit=debits,
                    running_balance=running_balance
                )
                journal_entries.append(entry)
    
    
    return journal_entries 
