"""
Database schema migration helpers.
Ensures new columns added to SQLite models are automatically synchronized
without requiring manual DROP TABLE or data loss.
"""
import sqlite3
import logging
from app.core.config import BASE_DIR

logger = logging.getLogger(__name__)


def migrate_sqlite_tables():
    """Checks SQLite schema and adds missing columns if necessary."""
    db_path = BASE_DIR / "heritage_monitoring.db"
    if not db_path.exists():
        return


    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Check reconstructions table
        cursor.execute("PRAGMA table_info(reconstructions)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        if existing_cols:
            recon_columns_to_add = [
                ("engine_version", "VARCHAR(100)"),
                ("current_stage", "VARCHAR(50) DEFAULT 'IDLE'"),
                ("progress_percent", "INTEGER DEFAULT 0"),
                ("workspace_path", "VARCHAR(500)"),
                ("log_path", "VARCHAR(500)"),
                ("registered_image_count", "INTEGER DEFAULT 0"),
                ("sparse_point_count", "INTEGER DEFAULT 0"),
                ("dense_point_count", "INTEGER DEFAULT 0"),
                ("mesh_vertex_count", "INTEGER DEFAULT 0"),
                ("mesh_triangle_count", "INTEGER DEFAULT 0"),
                ("camera_poses", "JSON"),
                ("bounding_box", "JSON"),
                ("metadata_json", "JSON"),
                ("is_demo", "BOOLEAN DEFAULT 0"),
                ("error_message", "TEXT"),
                ("started_at", "DATETIME"),
            ]

            for col_name, col_type in recon_columns_to_add:
                if col_name not in existing_cols:
                    try:
                        cursor.execute(f"ALTER TABLE reconstructions ADD COLUMN {col_name} {col_type}")
                        logger.info(f"Added column '{col_name}' to reconstructions table.")
                    except sqlite3.OperationalError as ex:
                        logger.warning(f"Could not add column {col_name}: {ex}")

        # Check material_detections table
        cursor.execute("PRAGMA table_info(material_detections)")
        mat_cols = {row[1] for row in cursor.fetchall()}
        if mat_cols:
            mat_columns_to_add = [
                ("reconstruction_id", "VARCHAR(36)"),
                ("material_class", "VARCHAR(50) DEFAULT 'sandstone'"),
                ("status", "VARCHAR(50) DEFAULT 'CONFIDENT'"),
                ("top_k_predictions", "JSON"),
                ("bounding_box", "JSON"),
                ("model_name", "VARCHAR(100) DEFAULT 'DemoMaterialClassifier'"),
                ("model_version", "VARCHAR(50) DEFAULT 'v1.0-demo'"),
                ("inference_mode", "VARCHAR(50) DEFAULT 'demo'"),
                ("is_demo", "BOOLEAN DEFAULT 1"),
                ("notes", "TEXT"),
            ]
            for col_name, col_type in mat_columns_to_add:
                if col_name not in mat_cols:
                    try:
                        cursor.execute(f"ALTER TABLE material_detections ADD COLUMN {col_name} {col_type}")
                        logger.info(f"Added column '{col_name}' to material_detections table.")
                    except sqlite3.OperationalError as ex:
                        logger.warning(f"Could not add column {col_name}: {ex}")

        # Check deterioration_detections table
        cursor.execute("PRAGMA table_info(deterioration_detections)")
        det_cols = {row[1] for row in cursor.fetchall()}
        if det_cols:
            det_columns_to_add = [
                ("reconstruction_id", "VARCHAR(36)"),
                ("material_class", "VARCHAR(50) DEFAULT 'UNKNOWN'"),
                ("material_confidence", "FLOAT"),
                ("material_association_status", "VARCHAR(50) DEFAULT 'MATERIAL_ASSOCIATION_UNAVAILABLE'"),
                ("candidate_materials", "JSON"),
                ("status", "VARCHAR(50) DEFAULT 'CONFIDENT'"),
                ("polygon", "JSON"),
                ("mask_reference", "VARCHAR(500)"),
                ("model_name", "VARCHAR(100) DEFAULT 'DemoDeteriorationDetector'"),
                ("model_version", "VARCHAR(50) DEFAULT 'v1.0-demo'"),
                ("inference_mode", "VARCHAR(50) DEFAULT 'demo'"),
                ("is_demo", "BOOLEAN DEFAULT 1"),
                ("notes", "TEXT"),
            ]
            for col_name, col_type in det_columns_to_add:
                if col_name not in det_cols:
                    try:
                        cursor.execute(f"ALTER TABLE deterioration_detections ADD COLUMN {col_name} {col_type}")
                        logger.info(f"Added column '{col_name}' to deterioration_detections table.")
                    except sqlite3.OperationalError as ex:
                        logger.warning(f"Could not add column {col_name}: {ex}")

        # Create deterioration_3d_mappings table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deterioration_3d_mappings (
                id VARCHAR(36) PRIMARY KEY,
                detection_id VARCHAR(36) NOT NULL,
                reconstruction_id VARCHAR(36) NOT NULL,
                survey_id VARCHAR(36) NOT NULL,
                image_id VARCHAR(36) NOT NULL,
                world_x FLOAT,
                world_y FLOAT,
                world_z FLOAT,
                image_x FLOAT,
                image_y FLOAT,
                ray_origin JSON,
                ray_direction JSON,
                intersection_distance FLOAT,
                mapping_method VARCHAR(50) DEFAULT 'MESH_RAYCAST',
                mapping_status VARCHAR(50) DEFAULT 'MAPPED',
                surface_source VARCHAR(50) DEFAULT 'DENSE_MESH',
                reprojection_error_px FLOAT,
                scale_status VARCHAR(50) DEFAULT 'LOCAL',
                sampling_strategy VARCHAR(50) DEFAULT 'CENTER_ONLY',
                sample_point_count INTEGER DEFAULT 1,
                mapped_point_count INTEGER DEFAULT 1,
                deterioration_type VARCHAR(50) NOT NULL,
                deterioration_confidence FLOAT NOT NULL,
                severity_hint VARCHAR(50) DEFAULT 'moderate',
                material_class VARCHAR(50) DEFAULT 'UNKNOWN',
                material_confidence FLOAT,
                material_association_status VARCHAR(50) DEFAULT 'MATERIAL_ASSOCIATION_UNAVAILABLE',
                is_demo BOOLEAN DEFAULT 1,
                inference_mode VARCHAR(50) DEFAULT 'demo',
                notes TEXT,
                created_at DATETIME,
                FOREIGN KEY (detection_id) REFERENCES deterioration_detections (id) ON DELETE CASCADE,
                FOREIGN KEY (reconstruction_id) REFERENCES reconstructions (id) ON DELETE CASCADE,
                FOREIGN KEY (survey_id) REFERENCES surveys (id) ON DELETE CASCADE,
                FOREIGN KEY (image_id) REFERENCES images (id) ON DELETE CASCADE
            )
        """)

        # Create deterioration_3d_mapping_points table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deterioration_3d_mapping_points (
                id VARCHAR(36) PRIMARY KEY,
                mapping_id VARCHAR(36) NOT NULL,
                point_type VARCHAR(50) DEFAULT 'center',
                image_x FLOAT NOT NULL,
                image_y FLOAT NOT NULL,
                world_x FLOAT,
                world_y FLOAT,
                world_z FLOAT,
                intersection_distance FLOAT,
                reprojection_error_px FLOAT,
                mapping_status VARCHAR(50) DEFAULT 'MAPPED',
                created_at DATETIME,
                FOREIGN KEY (mapping_id) REFERENCES deterioration_3d_mappings (id) ON DELETE CASCADE
            )
        """)

        # Create temporal_comparisons table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temporal_comparisons (
                id VARCHAR(36) PRIMARY KEY,
                site_id VARCHAR(36) NOT NULL,
                baseline_survey_id VARCHAR(36) NOT NULL,
                comparison_survey_id VARCHAR(36) NOT NULL,
                baseline_reconstruction_id VARCHAR(36),
                comparison_reconstruction_id VARCHAR(36),
                alignment_status VARCHAR(50) DEFAULT 'PENDING',
                alignment_method VARCHAR(50) DEFAULT 'ICP_POINT_TO_POINT',
                transformation_matrix JSON,
                fitness FLOAT,
                rmse FLOAT,
                correspondence_count INTEGER DEFAULT 0,
                scale_status VARCHAR(50) DEFAULT 'LOCAL',
                change_detection_method VARCHAR(50) DEFAULT 'POINT_TO_POINT_DISTANCE',
                change_threshold FLOAT DEFAULT 0.02,
                damage_matching_distance_threshold FLOAT DEFAULT 0.15,
                status VARCHAR(50) DEFAULT 'PENDING',
                elapsed_days INTEGER,
                summary_metrics JSON,
                is_demo BOOLEAN DEFAULT 1,
                inference_mode VARCHAR(50) DEFAULT 'demo',
                notes TEXT,
                error_message TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY (site_id) REFERENCES sites (id) ON DELETE CASCADE,
                FOREIGN KEY (baseline_survey_id) REFERENCES surveys (id) ON DELETE CASCADE,
                FOREIGN KEY (comparison_survey_id) REFERENCES surveys (id) ON DELETE CASCADE,
                FOREIGN KEY (baseline_reconstruction_id) REFERENCES reconstructions (id) ON DELETE SET NULL,
                FOREIGN KEY (comparison_reconstruction_id) REFERENCES reconstructions (id) ON DELETE SET NULL
            )
        """)

        # Create temporal_change_records table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temporal_change_records (
                id VARCHAR(36) PRIMARY KEY,
                comparison_id VARCHAR(36) NOT NULL,
                site_id VARCHAR(36) NOT NULL,
                baseline_survey_id VARCHAR(36) NOT NULL,
                comparison_survey_id VARCHAR(36) NOT NULL,
                change_status VARCHAR(50) NOT NULL,
                deterioration_type VARCHAR(50) NOT NULL,
                material_class VARCHAR(50) DEFAULT 'UNKNOWN',
                material_status VARCHAR(50) DEFAULT 'CONSISTENT',
                baseline_mapping_id VARCHAR(36),
                comparison_mapping_id VARCHAR(36),
                baseline_x FLOAT,
                baseline_y FLOAT,
                baseline_z FLOAT,
                comparison_x FLOAT,
                comparison_y FLOAT,
                comparison_z FLOAT,
                spatial_distance FLOAT,
                geometry_distance FLOAT,
                baseline_image_id VARCHAR(36),
                comparison_image_id VARCHAR(36),
                baseline_confidence FLOAT,
                comparison_confidence FLOAT,
                baseline_material_class VARCHAR(50),
                comparison_material_class VARCHAR(50),
                scale_status VARCHAR(50) DEFAULT 'LOCAL',
                is_demo BOOLEAN DEFAULT 1,
                notes TEXT,
                created_at DATETIME,
                FOREIGN KEY (comparison_id) REFERENCES temporal_comparisons (id) ON DELETE CASCADE,
                FOREIGN KEY (baseline_mapping_id) REFERENCES deterioration_3d_mappings (id) ON DELETE SET NULL,
                FOREIGN KEY (comparison_mapping_id) REFERENCES deterioration_3d_mappings (id) ON DELETE SET NULL
            )
        """)

        conn.commit()
    except Exception as e:
        logger.error(f"Migration error: {e}")
    finally:
        conn.close()


