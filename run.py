import json
import os
from urllib.request import Request

from dotenv import load_dotenv
from read_gotyme_bank_statement import process_bank_statement

load_dotenv()

request = Request(
    method="POST",
    url="http://testinglang.com",
    headers={"Content-Type": "application/json"},
    data=json.dumps({"file": os.getenv("TEST_PDF_LINK")}),
)

process_bank_statement(request)
