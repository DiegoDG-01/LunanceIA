from sqlalchemy import BigInteger, Integer

# BIGINT en MySQL; en SQLite (tests) solo INTEGER PRIMARY KEY es autoincremental.
BigIntId = BigInteger().with_variant(Integer(), "sqlite")
