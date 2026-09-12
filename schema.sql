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

CREATE TABLE IF NOT EXISTS orders (
    number VARCHAR(40) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    attraction_id INT NOT NULL,
    attraction_name VARCHAR(255) NOT NULL,
    attraction_address VARCHAR(500) NOT NULL,
    attraction_image VARCHAR(2048) NOT NULL,
    trip_date DATE NOT NULL,
    trip_time VARCHAR(20) NOT NULL,
    price INT NOT NULL,
    contact_name VARCHAR(40) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    contact_phone VARCHAR(16) NOT NULL,
    status ENUM('UNPAID', 'PAID') NOT NULL DEFAULT 'UNPAID',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users (id),
    CONSTRAINT fk_orders_attraction FOREIGN KEY (attraction_id) REFERENCES attractions (id),
    INDEX idx_orders_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_number VARCHAR(40) NOT NULL,
    status INT NULL,
    message VARCHAR(255) NOT NULL,
    rec_trade_id VARCHAR(64) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_payments_order UNIQUE (order_number),
    CONSTRAINT fk_payments_order FOREIGN KEY (order_number) REFERENCES orders (number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
