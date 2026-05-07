"""
0001_fts_and_audit.py
- Add name_tsv tsvector column + GIN index to ubid_entities
- Add DB trigger that populates name_tsv from linked source record names
- Add audit_events table
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR, JSONB

revision = "0001"
down_revision = "0d752d3dedec"
branch_labels = None
depends_on = None


def upgrade():
    # ── audit_events ──────────────────────────────────────────────────────────
    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("actor", sa.String(100), nullable=False),
        sa.Column("target_id", sa.String(80), nullable=True),
        sa.Column("detail", JSONB, nullable=True, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_audit_event_type", "audit_events", ["event_type"])
    op.create_index("idx_audit_actor",      "audit_events", ["actor"])
    op.create_index("idx_audit_created",    "audit_events", ["created_at"])

    # ── name_tsv on ubid_entities ─────────────────────────────────────────────
    op.add_column("ubid_entities", sa.Column("name_tsv", TSVECTOR, nullable=True))
    op.create_index(
        "idx_ubid_name_tsv", "ubid_entities", ["name_tsv"],
        postgresql_using="gin"
    )

    # ── Function + trigger to keep name_tsv up to date ───────────────────────
    # We collect business names from all 4 dept tables via the source_links,
    # concatenate them, and build the tsvector for the owning ubid_entity.
    op.execute("""
        CREATE OR REPLACE FUNCTION ubid_name_tsv_refresh(p_ubid TEXT)
        RETURNS void LANGUAGE plpgsql AS $$
        DECLARE
            combined_text TEXT := '';
        BEGIN
            SELECT string_agg(name, ' ') INTO combined_text
            FROM (
                SELECT se.business_name AS name
                  FROM ubid_source_links usl
                  JOIN dept_shop_establishment se ON se.se_reg_no = usl.source_record_id
                 WHERE usl.ubid = p_ubid AND usl.source_system = 'shop_establishment' AND usl.is_active
                UNION ALL
                SELECT f.factory_name
                  FROM ubid_source_links usl
                  JOIN dept_factories f ON f.factory_licence_no = usl.source_record_id
                 WHERE usl.ubid = p_ubid AND usl.source_system = 'factories' AND usl.is_active
                UNION ALL
                SELECT l.employer_name
                  FROM ubid_source_links usl
                  JOIN dept_labour l ON l.employer_code = usl.source_record_id
                 WHERE usl.ubid = p_ubid AND usl.source_system = 'labour' AND usl.is_active
                UNION ALL
                SELECT k.unit_name
                  FROM ubid_source_links usl
                  JOIN dept_kspcb k ON k.consent_order_no = usl.source_record_id
                 WHERE usl.ubid = p_ubid AND usl.source_system = 'kspcb' AND usl.is_active
            ) names;

            UPDATE ubid_entities
               SET name_tsv = to_tsvector('english', coalesce(combined_text, ''))
             WHERE ubid = p_ubid;
        END;
        $$;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION trg_ubid_source_link_tsv()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                PERFORM ubid_name_tsv_refresh(OLD.ubid);
            ELSE
                PERFORM ubid_name_tsv_refresh(NEW.ubid);
            END IF;
            RETURN NULL;
        END;
        $$;
    """)

    op.execute("""
        CREATE TRIGGER trg_source_link_tsv
        AFTER INSERT OR UPDATE OR DELETE ON ubid_source_links
        FOR EACH ROW EXECUTE FUNCTION trg_ubid_source_link_tsv();
    """)

    # Backfill name_tsv for all existing UBIDs
    op.execute("""
        SELECT ubid_name_tsv_refresh(ubid) FROM ubid_entities;
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_source_link_tsv ON ubid_source_links;")
    op.execute("DROP FUNCTION IF EXISTS trg_ubid_source_link_tsv();")
    op.execute("DROP FUNCTION IF EXISTS ubid_name_tsv_refresh(TEXT);")
    op.drop_index("idx_ubid_name_tsv", table_name="ubid_entities")
    op.drop_column("ubid_entities", "name_tsv")
    op.drop_table("audit_events")
