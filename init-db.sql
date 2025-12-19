-- Script de inicialización de base de datos para Sistema ICA
-- Este script se ejecuta automáticamente al crear el contenedor de PostgreSQL

-- Asegurar que la base de datos existe
SELECT 'CREATE DATABASE ica_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ica_db')\gexec

-- Conectar a la base de datos
\c ica_db

-- Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Configurar zona horaria
SET timezone = 'America/Bogota';

-- Mensaje de confirmación
SELECT 'Base de datos ICA inicializada correctamente' AS status;
