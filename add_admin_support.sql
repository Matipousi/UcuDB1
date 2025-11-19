-- Add admin support to UCU_SalasDeEstudio database
-- This script adds an is_admin column to the participante table
-- and sets the user with email "matipousi22@gmail.com" as admin

USE UCU_SalasDeEstudio;

-- Add is_admin column to participante table
ALTER TABLE participante 
ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL;

-- Set the user with email "matipousi22@gmail.com" as admin
UPDATE participante 
SET is_admin = TRUE 
WHERE email = 'matipousi22@gmail.com';

-- Verify the update
SELECT ci, nombre, apellido, email, is_admin 
FROM participante 
WHERE email = 'matipousi22@gmail.com';

