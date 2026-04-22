DROP DATABASE IF EXISTS petshop;
CREATE DATABASE petshop;
USE petshop;

-- PETS
CREATE TABLE pets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100),
    nascimento DATE,
    especie VARCHAR(50),
    raca VARCHAR(100)
);

INSERT INTO pets (nome, nascimento, especie, raca) VALUES
('Marina da Silva', '2015-09-26', 'Canis lupus familiaris','Labrador Retriever'),
('Olivia Rodrigues', '2020-01-05','Canis lupus familiaris', 'Pastor Alemão'),
('Donatella Vieira', '2023-06-22', 'Canis lupus familiaris', 'Golden Retriever');

-- EVENTOS (AGENDA)
CREATE TABLE eventos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pet_id INT,
    data DATE,
    hora TIME,
    tipo VARCHAR(50),
    descricao VARCHAR(200),
    local VARCHAR(100),
    observacoes TEXT,
    FOREIGN KEY (pet_id) REFERENCES pets(id)
);

INSERT INTO eventos (pet_id, data, hora, tipo, descricao, local, observacoes) VALUES
(1, '2026-04-25', '10:00:00', 'Banho', 'Banho completo', 'PetShop Centro', 'Usar shampoo neutro'),
(2, '2026-04-26', '14:30:00', 'Consulta', 'Consulta veterinária', 'Clínica Pet', 'Verificar vacinas'),
(3, '2026-04-27', '09:00:00', 'Tosa', 'Tosa higiênica', 'PetShop Centro', 'Corte leve');

-- ADMIN
CREATE TABLE admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100),
    senha VARCHAR(100)
);

INSERT INTO admin (email, senha) VALUES 
('admin@gmail.com', '123456');

-- FUNCIONÁRIOS
CREATE TABLE funcionarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100),
    cargo VARCHAR(100),
    salario DECIMAL(10,2),
    telefone VARCHAR(20)
);

INSERT INTO funcionarios (nome, cargo, salario, telefone) VALUES 
('Isabela Silva dos Santos', 'Assistente administrativo', 1400.00, '41999999999'),
('Carlos Pereira', 'Veterinário', 3500.00, '41988888888'),
('Ana Souza', 'Banhista', 1800.00, '41977777777');
