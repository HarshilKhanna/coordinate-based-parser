from pydantic import BaseModel
from typing import Optional


class CauseListEntry(BaseModel):
    item_number: Optional[int] = None
    court_name: str = ""
    court_no: str = ""
    listing_date: str = ""
    case_number: Optional[str] = None
    petitioner: Optional[str] = None
    respondent: Optional[str] = None
    advocates: Optional[str] = None
