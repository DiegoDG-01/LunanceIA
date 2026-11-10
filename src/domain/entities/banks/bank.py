from dataclasses import dataclass


@dataclass
class Bank:
    id: int
    name: str
    code: str
    country: str = "MX"
    logo_url: str | None = None
    color: str | None = None
    is_active: bool = True

    @classmethod
    def create_new(
        cls,
        name: str,
        code: str,
        country: str = "MX",
        logo_url: str | None = None,
        color: str | None = None,
    ):
        if not name.strip():
            raise ValueError("Bank name cannot be empty")
        if not code.strip():
            raise ValueError("Bank code cannot be empty")

        return cls(
            id=0,
            name=name.strip(),
            code=code.strip(),
            country=country.upper(),
            logo_url=logo_url,
            color=color,
        )
