import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()


def init_database():
    """Inicializa la base de datos con las tablas necesarias"""

    connection = None
    try:
        # Conexión a PostgreSQL
        connection = psycopg2.connect(
            host="localhost",
            port="5432",
            database="email_automation",
            user="admin",
            password="password123"
        )

        cursor = connection.cursor()

        # Crear tabla de emails clasificados
        create_table_query = """
        CREATE TABLE IF NOT EXISTS classified_emails (
            id SERIAL PRIMARY KEY,
            sender_email VARCHAR(255) NOT NULL,
            sender_domain VARCHAR(100),
            subject TEXT,
            email_content TEXT,
            category VARCHAR(50) NOT NULL,
            confidence FLOAT,
            urgency_score INTEGER,
            urgency_level VARCHAR(20),
            sentiment VARCHAR(20),
            suggested_response TEXT,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS email_actions (
            id SERIAL PRIMARY KEY,
            email_id INTEGER REFERENCES classified_emails(id),
            action_type VARCHAR(50) NOT NULL,
            action_details JSONB,
            performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_category ON classified_emails(category);
        CREATE INDEX IF NOT EXISTS idx_urgency ON classified_emails(urgency_score);
        CREATE INDEX IF NOT EXISTS idx_received_at ON classified_emails(received_at);
        """

        cursor.execute(create_table_query)
        connection.commit()

        print("✅ Base de datos inicializada correctamente")

    except Exception as error:
        print(f"❌ Error inicializando base de datos: {error}")
    finally:
        if connection:
            cursor.close()
            connection.close()


if __name__ == "__main__":
    init_database()