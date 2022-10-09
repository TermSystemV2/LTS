import typing as t

from pydantic import BaseModel,Field


class StuAnalysisBar(BaseModel):
    stuTermBar: str = Field(default='11',description="学期选择下拉框")
    stuClassID: str = Field(default='',description="学生学号")

