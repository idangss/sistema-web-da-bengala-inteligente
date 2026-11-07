-- Rodar UMA vez como root, depois do schema.sql.
-- api_bengala: o usuário que o Django usa no dia a dia (sem DROP, sem ALTER).

CREATE USER IF NOT EXISTS 'api_bengala'@'localhost' IDENTIFIED BY 'senha-forte-aqui';
GRANT SELECT, INSERT, UPDATE, DELETE ON bengala.* TO 'api_bengala'@'localhost';

-- Opcional: usuário só leitura para consultas da apresentação.
CREATE USER IF NOT EXISTS 'leitura'@'localhost' IDENTIFIED BY 'outra-senha';
GRANT SELECT ON bengala.* TO 'leitura'@'localhost';

FLUSH PRIVILEGES;
