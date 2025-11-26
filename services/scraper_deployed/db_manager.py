import os

# from collections.abc import Mapping, Sequence
# from typing import Any

import psycopg
from psycopg import sql


class PostgresDBManager:
    def __init__(self, url_column):
        self._dsn = os.environ.get("DATABASE_URL")
        if not self._dsn:
            raise RuntimeError("Postgres DSN not provided and DATABASE_URL is unset")
        self._table_name = "articles"
        self._url_column = url_column

    def filter_new_urls(self, urls):
        """
        This function is to be used in the scrapers as soon as the scraper identifies the article
        URLs. It is designed to filter out any article URL that has already been scraped and
        added to the DB
        """
        ordered_unique_urls = list(dict.fromkeys(urls))
        if not ordered_unique_urls:
            return []
        query = sql.SQL("SELECT {column} FROM {table} WHERE {column} = ANY (%s)").format(
            column=sql.Identifier(self._url_column),
            table=sql.Identifier(self._table_name),
        )
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (ordered_unique_urls,))
                existing = {row[0] for row in cur.fetchall()}
        return [url for url in ordered_unique_urls if url not in existing]

    def insert_records(self, records):
        """
        This function is to be used after the scraper is done scraping, to add the nes articles to
        the database
        """
        if not records:
            return 0
        try:
            urls = [record[self._url_column] for record in records]
        except KeyError as exc:
            raise KeyError(f"Record missing required URL field '{self._url_column}'") from exc
        new_urls = set(self.filter_new_urls(urls))
        records_to_insert = [record for record in records if record[self._url_column] in new_urls]
        if not records_to_insert:
            return 0
        columns = list(records_to_insert[0].keys())
        column_set = set(columns)
        for record in records_to_insert:
            if set(record.keys()) != column_set:
                raise ValueError("All records must contain the same columns")
        query = sql.SQL("INSERT INTO {table} ({columns}) VALUES ({placeholders})").format(
            table=sql.Identifier(self._table_name),
            columns=sql.SQL(", ").join(sql.Identifier(column) for column in columns),
            placeholders=sql.SQL(", ").join(sql.Placeholder() for _ in columns),
        )
        inserted_count = 0
        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                for record in records_to_insert:
                    values = [record[column] for column in columns]
                    cur.execute(query, values)
                    inserted_count += cur.rowcount
        return inserted_count

    def fetch_articles_without_summary(self, limit=None):
        """Return articles that are missing a summary field."""
        base_query = sql.SQL(
            "SELECT id, article_id, title, content FROM {table} "
            "WHERE summary IS NULL OR summary = '' "
            "ORDER BY fetched_at NULLS LAST, id ASC"
        ).format(table=sql.Identifier(self._table_name))

        params = ()
        if limit is not None:
            base_query += sql.SQL(" LIMIT %s")
            params = (limit,)

        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                if params:
                    cur.execute(base_query, params)
                else:
                    cur.execute(base_query)
                rows = cur.fetchall()

        columns = ("id", "article_id", "title", "content")
        return [dict(zip(columns, row)) for row in rows]

    def update_article_summary(self, article_id, summary):
        query = sql.SQL("UPDATE {table} SET summary = %s WHERE article_id = %s").format(
            table=sql.Identifier(self._table_name)
        )

        with psycopg.connect(self._dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (summary, article_id))
                updated = cur.rowcount
            conn.commit()

        return updated


if __name__ == "__main__":
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("Set DATABASE_URL before running this module.")

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT schemaname, tablename
                FROM pg_catalog.pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                ORDER BY schemaname, tablename;
                """
            )
            tables = cur.fetchall()

    table_names = [f"{schema}.{table}" for schema, table in tables]
    print("Discovered tables:")
    for name in table_names:
        print(f"- {name}")
