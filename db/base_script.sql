CREATE TABLE IF NOT EXISTS `Group` (
	`name` TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS `Subject` (
	`name` TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS `WorkDay` (
	`id` integer primary key NOT NULL UNIQUE,
	`date` TEXT NOT NULL,
	`subject_name` TEXT NOT NULL,
	`group_name` TEXT NOT NULL,
	`semestr` INTEGER NOT NULL,
FOREIGN KEY(`subject_name`) REFERENCES `Subject`(`name`),
FOREIGN KEY(`group_name`) REFERENCES `Group`(`name`)
);
CREATE TABLE IF NOT EXISTS `Curriculum` (
	`id` integer primary key NOT NULL UNIQUE,
	`semestr` INTEGER NOT NULL,
	`total_hour` INTEGER NOT NULL,
	`group_name` TEXT NOT NULL,
	`subject_name` TEXT NOT NULL,
FOREIGN KEY(`group_name`) REFERENCES `Group`(`name`),
FOREIGN KEY(`subject_name`) REFERENCES `Subject`(`name`)
);