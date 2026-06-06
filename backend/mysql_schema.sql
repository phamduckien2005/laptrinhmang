CREATE DATABASE IF NOT EXISTS unilib
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE unilib;

CREATE TABLE IF NOT EXISTS `category` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(120) NOT NULL,
  `description` VARCHAR(255) NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_category_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `book` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `google_book_id` VARCHAR(100) NULL,
  `title` VARCHAR(255) NULL,
  `author` VARCHAR(255) NULL,
  `description` TEXT NULL,
  `isbn` VARCHAR(100) NULL,
  `image` VARCHAR(500) NULL,
  `available` TINYINT(1) NULL DEFAULT 1,
  `file_path` VARCHAR(500) NULL,
  `quantity` INT NULL DEFAULT 1,
  `shelf_location` VARCHAR(100) NULL,
  `category_id` INT NULL,
  PRIMARY KEY (`id`),
  INDEX `idx_book_google_book_id` (`google_book_id`),
  INDEX `idx_book_title` (`title`),
  INDEX `idx_book_author` (`author`),
  INDEX `idx_book_isbn` (`isbn`),
  INDEX `idx_book_category_id` (`category_id`),
  CONSTRAINT `fk_book_category`
    FOREIGN KEY (`category_id`) REFERENCES `category` (`id`)
    ON UPDATE CASCADE
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(80) NOT NULL,
  `email` VARCHAR(255) NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `full_name` VARCHAR(255) NULL,
  `role` VARCHAR(50) NULL DEFAULT 'user',
  `is_locked` TINYINT(1) NULL DEFAULT 0,
  `created_at` DATETIME NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_username` (`username`),
  UNIQUE KEY `uq_user_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `borrow_record` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `book_id` INT NOT NULL,
  `request_date` DATETIME NULL,
  `borrow_date` DATETIME NOT NULL,
  `due_date` DATETIME NULL,
  `return_date` DATETIME NULL,
  `returned` TINYINT(1) NULL DEFAULT 0,
  `status` VARCHAR(30) NULL DEFAULT 'pending',
  `reject_reason` VARCHAR(255) NULL,
  `fine_amount` INT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  INDEX `idx_borrow_record_user_id` (`user_id`),
  INDEX `idx_borrow_record_book_id` (`book_id`),
  INDEX `idx_borrow_record_returned` (`returned`),
  INDEX `idx_borrow_record_status` (`status`),
  CONSTRAINT `fk_borrow_record_user`
    FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  CONSTRAINT `fk_borrow_record_book`
    FOREIGN KEY (`book_id`) REFERENCES `book` (`id`)
    ON UPDATE CASCADE
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `review` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `book_id` INT NOT NULL,
  `rating` INT NULL DEFAULT 5,
  `comment` TEXT NULL,
  `hidden` TINYINT(1) NULL DEFAULT 0,
  `created_at` DATETIME NULL,
  PRIMARY KEY (`id`),
  INDEX `idx_review_user_id` (`user_id`),
  INDEX `idx_review_book_id` (`book_id`),
  CONSTRAINT `fk_review_user`
    FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
    ON UPDATE CASCADE
    ON DELETE CASCADE,
  CONSTRAINT `fk_review_book`
    FOREIGN KEY (`book_id`) REFERENCES `book` (`id`)
    ON UPDATE CASCADE
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `notification` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `title` VARCHAR(255) NOT NULL,
  `message` TEXT NOT NULL,
  `notification_type` VARCHAR(50) NULL DEFAULT 'general',
  `created_at` DATETIME NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `violation_report` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NULL,
  `book_id` INT NULL,
  `report_type` VARCHAR(100) NOT NULL,
  `message` TEXT NULL,
  `status` VARCHAR(30) NULL DEFAULT 'open',
  `created_at` DATETIME NULL,
  PRIMARY KEY (`id`),
  INDEX `idx_violation_report_user_id` (`user_id`),
  INDEX `idx_violation_report_book_id` (`book_id`),
  INDEX `idx_violation_report_status` (`status`),
  CONSTRAINT `fk_violation_report_user`
    FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
    ON UPDATE CASCADE
    ON DELETE SET NULL,
  CONSTRAINT `fk_violation_report_book`
    FOREIGN KEY (`book_id`) REFERENCES `book` (`id`)
    ON UPDATE CASCADE
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO `category` (`name`) VALUES
  ('CNTT'),
  ('Kinh tế'),
  ('Marketing'),
  ('Ngoại ngữ'),
  ('Tiểu thuyết');
