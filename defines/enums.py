from enum import Enum


class EditType(Enum):
    ADDED = 1
    DELETED = 2
    MODIFIED = 3
    RENAMED = 4
    UNKNOWN = 5


class CommandType(Enum):
    Help = "/help"
    Review = "/review"
    Describe = "/describe"
    Labels = "/labels"
