from pydantic_settings import BaseSettings


class MCPSettings(BaseSettings):
    MCP_HOST: str = "localhost"
    MCP_PORT: int = 8001
    LUNANCE_API_BASE_URL: str = "http://localhost:8000"

    MCP_ALLOWED_HOSTS: str = "localhost:8001,127.0.0.1:8001"
    MCP_ALLOWED_ORIGINS: str = "http://localhost:8001,http://127.0.0.1:8001"

    @property
    def allowed_hosts(self) -> list[str]:
        return [h.strip() for h in self.MCP_ALLOWED_HOSTS.split(",") if h.strip()]

    @property
    def allowed_origins(self) -> list[str]:
        return [h.strip() for h in self.MCP_ALLOWED_ORIGINS.split(",") if h.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


mcp_settings = MCPSettings()
