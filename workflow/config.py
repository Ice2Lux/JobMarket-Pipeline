from pydantic import BaseModel


class WorkflowConfig(BaseModel):
    api_auth_url : str
    api_base_url : str
    id_client: str # Best practice, à renseigner dans Azure Key-vault
    secret_key: str # Best practice, à renseigner dans Azure Key-vault
    output_dir: str
