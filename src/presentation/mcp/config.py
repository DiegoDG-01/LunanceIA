from pydantic_settings import BaseSettings


class MCPSettings(BaseSettings):
    MCP_HOST: str = "localhost"
    MCP_PORT: int = 8001
    LUNANCE_API_BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


mcp_settings = MCPSettings()
