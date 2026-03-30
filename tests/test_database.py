from __future__ import annotations

from sqlalchemy import text

from caixa_scanner.database import SessionLocal, engine, init_db


def test_init_db_adds_new_edital_columns_for_existing_sqlite_table():
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS properties"))
        connection.execute(
            text(
                """
                CREATE TABLE properties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_code VARCHAR(32) UNIQUE,
                    uf VARCHAR(2)
                )
                """
            )
        )

    init_db()

    with engine.begin() as connection:
        columns = connection.execute(text("PRAGMA table_info(properties)")).fetchall()

    column_names = {column[1] for column in columns}
    assert "edital_sale_mode" in column_names
    assert "edital_sale_date" in column_names
    assert "edital_payment_details" in column_names
    assert "edital_risk_notes" in column_names
