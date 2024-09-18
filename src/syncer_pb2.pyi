from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FileState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN_FILE_KEY: _ClassVar[FileState]
    FILE_NOT_PRESENT: _ClassVar[FileState]
    FILE_NOT_READABLE: _ClassVar[FileState]
    DOWNLOAD_POSSIBLE: _ClassVar[FileState]
UNKNOWN_FILE_KEY: FileState
FILE_NOT_PRESENT: FileState
FILE_NOT_READABLE: FileState
DOWNLOAD_POSSIBLE: FileState

class FileKey(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class FileDesc(_message.Message):
    __slots__ = ("state", "file_name", "last_modification_time", "file_size")
    STATE_FIELD_NUMBER: _ClassVar[int]
    FILE_NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_MODIFICATION_TIME_FIELD_NUMBER: _ClassVar[int]
    FILE_SIZE_FIELD_NUMBER: _ClassVar[int]
    state: FileState
    file_name: str
    last_modification_time: float
    file_size: int
    def __init__(self, state: _Optional[_Union[FileState, str]] = ..., file_name: _Optional[str] = ..., last_modification_time: _Optional[float] = ..., file_size: _Optional[int] = ...) -> None: ...

class FileChunk(_message.Message):
    __slots__ = ("content",)
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    content: bytes
    def __init__(self, content: _Optional[bytes] = ...) -> None: ...
