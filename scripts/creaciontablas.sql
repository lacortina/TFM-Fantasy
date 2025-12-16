CREATE DATABASE IF NOT EXISTS futbol;
USE futbol;

-- ==========================================================
--  TABLA: equipos (normalización de nombres)
-- ==========================================================


DROP TABLE IF EXISTS stats_partido_equipo;
DROP TABLE IF EXISTS stats_jugador;
DROP TABLE IF EXISTS dfequiposracha;
DROP TABLE IF EXISTS dfequipos;
DROP TABLE IF EXISTS partidos;
DROP TABLE IF EXISTS equipos;

CREATE TABLE equipos (
    id_equipo INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(80) UNIQUE NOT NULL
);

-- ==========================================================
--  TABLA: partidos (resultados_partidos.csv)
-- ==========================================================
CREATE TABLE partidos (
    id_partido INT AUTO_INCREMENT PRIMARY KEY,
    temporada VARCHAR(9) NOT NULL,
    jornada INT NOT NULL,
    fecha DATE NULL,
    id_local INT NOT NULL,
    id_visitante INT NOT NULL,
    goles_local INT,
    goles_visitante INT,
    lineup_url VARCHAR(255),
    FOREIGN KEY (id_local) REFERENCES equipos(id_equipo),
    FOREIGN KEY (id_visitante) REFERENCES equipos(id_equipo)
);

-- ==========================================================
--  TABLA: stats_jugador (player_stats.csv)
-- ==========================================================
CREATE TABLE stats_jugador (
    id_jugador INT AUTO_INCREMENT PRIMARY KEY,
    temporada VARCHAR(9) NOT NULL,
    nombre VARCHAR(100),
    id_equipo INT,
    minutos_totales INT,
    goles_totales INT,
    partidos_jugados INT,
    FOREIGN KEY (id_equipo) REFERENCES equipos(id_equipo)
);

-- ==========================================================
--  TABLA: stats_partido_equipo (team_stats.csv)
--  (cada fila = una estadística concreta en un partido)
-- ==========================================================
CREATE TABLE stats_partido_equipo (
    id_stat INT AUTO_INCREMENT PRIMARY KEY,
    temporada VARCHAR(9) NOT NULL,
    jornada INT,
    id_local INT,
    id_visitante INT,
    stat VARCHAR(100),
    valor_local FLOAT,
    valor_visitante FLOAT,
    FOREIGN KEY (id_local) REFERENCES equipos(id_equipo),
    FOREIGN KEY (id_visitante) REFERENCES equipos(id_equipo)
);

-- ==========================================================
--  TABLA: dfequipos (modelo partido a partido)
-- ==========================================================
CREATE TABLE dfequipos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    temporada VARCHAR(9) NOT NULL,
    id_equipo INT NOT NULL,
    jornada INT NOT NULL,
    localia TINYINT,
    partidos_jugados INT,
    goles_marcados_pp FLOAT,
    goles_encajados_pp FLOAT,
    victorias_pp FLOAT,
    empates_pp FLOAT,
    derrotas_pp FLOAT,
    amarillo_pp FLOAT,
    amarillo_rojo_pp FLOAT,
    corners_pp FLOAT,
    duelos_pp FLOAT,
    faltas_cometidas_pp FLOAT,
    fuera_de_juego_pp FLOAT,
    pases_exitosos_pp FLOAT,
    pases_ges_pp FLOAT,
    posesion_pp FLOAT,
    rojo_pp FLOAT,
    tiros_a_puerta_pp FLOAT,
    FOREIGN KEY (id_equipo) REFERENCES equipos(id_equipo)
);

-- ==========================================================
--  TABLA: dfequipos_racha
-- ==========================================================
CREATE TABLE dfequiposracha (
    id INT AUTO_INCREMENT PRIMARY KEY,
    temporada VARCHAR(9) NOT NULL,
    id_equipo INT NOT NULL,
    jornada INT NOT NULL,
    partidos_jugados INT,
    goles_marcados_pp FLOAT,
    goles_encajados_pp FLOAT,
    victorias_pp FLOAT,
    empates_pp FLOAT,
    amarillo_pp FLOAT,
    amarillo_rojo_pp FLOAT,
    corners_pp FLOAT,
    duelos_pp FLOAT,
    faltas_cometidas_pp FLOAT,
    fuera_de_juego_pp FLOAT,
    pases_exitosos_pp FLOAT,
    pases_ges_pp FLOAT,
    posesion_pp FLOAT,
    rojo_pp FLOAT,
    tiros_a_puerta_pp FLOAT,
    goles_marcados_racha FLOAT,
    goles_encajados_racha FLOAT,
    victoria_racha FLOAT,
    empate_racha FLOAT,
    derrota_racha FLOAT,
    amarillo_racha FLOAT,
    amarillo_rojo_racha FLOAT,
    corners_racha FLOAT,
    duelos_racha FLOAT,
    faltas_cometidas_racha FLOAT,
    fuera_de_juego_racha FLOAT,
    pases_exitosos_racha FLOAT,
    pases_ges_racha FLOAT,
    posesion_racha FLOAT,
    rojo_racha FLOAT,
    tiros_a_puerta_racha FLOAT,
    FOREIGN KEY (id_equipo) REFERENCES equipos(id_equipo)
);


