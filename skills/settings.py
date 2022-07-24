from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    @validator('*', pre=True)
    def replace_quotation_marks(cls,v):
        return v.replace("'","")

    GITLAB_API_ADDR: str
    GITLAB_TOKEN: str
    GITLAB_PROJECT_ID: int
    GITLAB_BRANCH_NAME: str
    GITLAB_CD_YAML_FILE: str


settings: Settings = Settings()
