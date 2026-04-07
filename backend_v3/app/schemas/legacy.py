from typing import Any, Literal

from pydantic import BaseModel, Field


class LegacyFilenameRequest(BaseModel):
    filename: str = Field(min_length=1)


class LegacyChatMessage(BaseModel):
    role: str = Field(min_length=1)
    content: str = Field(min_length=1)


class LegacyChatRequest(BaseModel):
    filename: str = Field(min_length=1)
    chat_history: list[LegacyChatMessage]


class LegacyTrainingRequest(BaseModel):
    filename: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    model_type: Literal["IsolationForest", "LocalOutlierFactor", "OneClassSVM"] = "IsolationForest"
    numerical_features: list[str] = Field(default_factory=list)
    categorical_features: list[str] = Field(default_factory=list)
    date_features: list[str] = Field(default_factory=list)
    enable_feature_engineering: bool = False
    card_id_column: str | None = None
    timestamp_column: str | None = None
    amount_column: str | None = None


class LegacyScoreFileRequest(BaseModel):
    model_name: str = Field(min_length=1)
    filename: str = Field(min_length=1)


class LegacyPredictRequest(BaseModel):
    model_name: str = Field(min_length=1)
    features: dict[str, Any]


class LegacyFraudCheckRequest(BaseModel):
    data_type: Literal["phone", "email", "url", "text"]
    value: str = Field(min_length=1)


class LegacyBlacklistRequest(BaseModel):
    data_type: Literal["phone", "email", "domain"]
    value: str = Field(min_length=1)
