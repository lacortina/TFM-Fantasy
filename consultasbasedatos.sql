CREATE DATABASE IF NOT EXISTS fantasy;
USE fantasy;
CREATE TABLE IF NOT EXISTS jugadores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100),
    equipo VARCHAR(100),
    posicion VARCHAR(50),
    precio DECIMAL(10,2),
    puntos INT,
    estado VARCHAR(50),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
%La contraseña Perr0d3is