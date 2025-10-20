CREATE TABLE "groups" (
	"name"	TEXT NOT NULL UNIQUE
);

CREATE TABLE "subjects" (
	"name"	TEXT NOT NULL UNIQUE
);

CREATE TABLE "workDays" (
	"id"	integer NOT NULL UNIQUE,
	"date"	TEXT NOT NULL,
	"subject_name"	TEXT NOT NULL,
	"group_name"	TEXT NOT NULL,
	"semester"	INTEGER NOT NULL,
	"hours"	INTEGER NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("group_name") REFERENCES "groups"("name"),
	FOREIGN KEY("subject_name") REFERENCES "subjects"("name")
);

CREATE TABLE "curriculums" (
	"id"	integer NOT NULL UNIQUE,
	"semester"	INTEGER NOT NULL,
	"total_hour"	INTEGER NOT NULL,
	"group_name"	TEXT NOT NULL,
	"subject_name"	TEXT NOT NULL,
	PRIMARY KEY("id"),
	FOREIGN KEY("group_name") REFERENCES "groups"("name"),
	FOREIGN KEY("subject_name") REFERENCES "subjects"("name")
);