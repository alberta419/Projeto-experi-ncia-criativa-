CREATE DATABASE petshop;
USE petshop;

-- PETS
CREATE TABLE pets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100),
    nascimento DATE,
    especie VARCHAR(10),
    raca VARCHAR(100)
);

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
CREATE TABLE admin (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100),
    senha VARCHAR(100)
);

INSERT INTO admin (email, senha)
VALUES ('admin@petzen.com', '123456');

-- FUNCIONÁRIOS
CREATE TABLE funcionarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100),
    cargo VARCHAR(100),
    salario DECIMAL(10,2),
    telefone VARCHAR(20)
);