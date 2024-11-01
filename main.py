from io import BytesIO
import json
import os
from dotenv import load_dotenv
import requests
import pdfplumber
from google.cloud import pubsub_v1

load_dotenv()

NOTION_ORGANIZATION = os.getenv("NOTION_ORGANIZATION")
NOTION_EXPENSES_DATABASE_ID = os.getenv("NOTION_EXPENSES_DATABASE_ID")
NOTION_EXPENSES_VIEW_ID = os.getenv("NOTION_EXPENSES_VIEW_ID")

ENTRIES_TO_IGNORE = [
    "Inbound interbank transfer",
    "Transfer to Go Save account",
    "Transfer from Go Save account",
]


def process_bank_statement(request):
    """Responds to any HTTP request.
    Args:
        request (flask.Request): HTTP request object.
    Returns:
        The response text or any set of values that can be turned into a
        Response object using
        `make_response <http://flask.pocoo.org/docs/1.0/api/#flask.Flask.make_response>`.
    """
    request_json = json.loads(request.data)

    file = request_json.get("file")
    journal_entries = _get_journal_entries(file)
    try:
        for entry in journal_entries:
            print(entry)
            _save_to_notion(entry.to_notion_expense_page())
        _alert_to_discord()
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}"

    return f"Donezo!"


class NotionPage:
    def __init__(self, organization, database_id, view_id, properties):
        self.organization = organization
        self.database_id = database_id
        self.view_id = view_id
        self.properties = properties

    def __str__(self):
        return f"Organization: {self.organization}\nDatabase ID: {self.database_id}\nView ID: {self.view_id}\nProperties: {self.properties}\n"

    def to_bytes_string(self):
        return json.dumps(
            {
                "organization": self.organization,
                "database-id": self.database_id,
                "view-id": self.view_id,
                "properties": self.properties,
            }
        ).encode("utf-8")


class JournalEntry:
    def __init__(self, date, details, credit, debit, running_balance):
        self.date = date
        self.details = details
        self.credit = credit
        self.debit = debit
        self.running_balance = running_balance

    def to_notion_expense_page(self):
        return NotionPage(
            organization=NOTION_ORGANIZATION,
            database_id=NOTION_EXPENSES_DATABASE_ID,
            view_id=NOTION_EXPENSES_VIEW_ID,
            properties=self._get_notion_expenses_properties(),
        )

    def _get_notion_expenses_properties(self):
        return [
            {
                "key": "Date Spent",
                "value": self.date,
            },
            {
                "key": "Name",
                "value": self.details,
            },
            {
                "key": "Amount",
                "value": self.debit,
            },
        ]

    def __str__(self):
        return f"Date: {self.date}\nDetails: {self.details}\nCredit: {self.credit}\nDebit: {self.debit}\nRunning Balance: {self.running_balance}\n"


def _get_journal_entries(file_url):
    response = requests.get(file_url)
    statement_pdf = BytesIO(response.content)

    journal_entries = []
    with pdfplumber.open(
        statement_pdf, password=os.getenv("GOTYME_BS_PASSWORD")
    ) as pdf:
        for page in pdf.pages:
            is_in_table = False
            for line in page.extract_text().split("\n"):
                if not is_in_table:
                    if line == "Date Details Credits Debits Running Balance":
                        is_in_table = True
                        continue
                    continue
                if is_in_table and line == "All figures are in PHP.":
                    break

                line_split = line.split()
                details = " ".join(line_split[1:-3])

                if details in ENTRIES_TO_IGNORE:
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
                    running_balance=running_balance,
                )
                journal_entries.append(entry)

    return journal_entries


def _save_to_notion(notion_page: NotionPage):
    print("Saving to notion...")
    token = os.popen("gcloud auth print-identity-token").read().strip()

    response = requests.post(
        "https://us-central1-mydas-stuff.cloudfunctions.net/notion-page-builder",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        data=notion_page.to_bytes_string(),
    )
    response.raise_for_status()
    print("HERE")
    print(response.text)


def _alert_to_discord():
    link_to_notion = f"https://www.notion.so/{NOTION_ORGANIZATION}/{NOTION_EXPENSES_DATABASE_ID}?v={NOTION_EXPENSES_VIEW_ID}&pvs=4"

    publisher = pubsub_v1.PublisherClient()
    message = json.dumps(
        {
            "channel-name": os.environ.get("DISCORD_ALERTS_CHANNEL_NAME"),
            "message": "Expenses have been sent to the notion page builder!",
            "link": link_to_notion,
        }
    ).encode("utf-8")

    topic_name = "projects/{project_id}/topics/{topic}".format(
        project_id=os.getenv("PROJECT"),
        topic=os.getenv("DISCORD_ALERT_PUBSUB_TOPIC"),
    )
    future = publisher.publish(topic_name, message)
    future.result()
