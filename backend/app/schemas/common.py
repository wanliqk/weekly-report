from pydantic import BaseModel


class ApiResponse[DataT](BaseModel):
    code: int = 0
    msg: str = "success"
    data: DataT
