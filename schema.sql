CREATE DATABASE IF NOT EXISTS taipei_day_trip
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE taipei_day_trip;

CREATE TABLE IF NOT EXISTS attractions (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    address VARCHAR(500) NOT NULL,
    transport TEXT NOT NULL,
    mrt VARCHAR(255) NULL,
    lat DECIMAL(10, 7) NOT NULL,
    lng DECIMAL(10, 7) NOT NULL,
    INDEX idx_attractions_category (category),
    INDEX idx_attractions_mrt (mrt),
    INDEX idx_attractions_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attraction_images (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    attraction_id INT NOT NULL,
    image_url VARCHAR(2048) NOT NULL,
    image_order INT UNSIGNED NOT NULL,
    CONSTRAINT fk_attraction_images_attraction
        FOREIGN KEY (attraction_id)
        REFERENCES attractions (id)
        ON DELETE CASCADE,
    CONSTRAINT uq_attraction_images_order
        UNIQUE (attraction_id, image_order),
    INDEX idx_attraction_images_attraction (attraction_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    CONSTRAINT uq_users_email UNIQUE (email)
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bookings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    attraction_id INT NOT NULL,
    date DATE NOT NULL,
    time VARCHAR(20) NOT NULL,
    price INT NOT NULL,

    CONSTRAINT uq_bookings_user
        UNIQUE (user_id),

    CONSTRAINT fk_bookings_user
        FOREIGN KEY (user_id)
        REFERENCES users (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_bookings_attraction
        FOREIGN KEY (attraction_id)
        REFERENCES attractions (id),

    INDEX idx_bookings_attraction (attraction_id)
) ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci;
