use TigerWallet;

drop table IF EXISTS Purchases;
drop table IF EXISTS MealPlans;
drop table IF EXISTS SessionData;
drop table IF EXISTS UserSettings;
drop table IF EXISTS UserInfo;

SHOW TABLES;
CREATE table UserInfo (
	uid varchar(37),
    first_name varchar(32),
    last_name varchar(32),
    pref_name varchar(32),
    first_sign_in datetime,
    last_sign_in datetime,
    total_auths int DEFAULT 0,
    primary key (uid)
);

SHOW TABLES;
CREATE table MealPlans (
	uid varchar(37),
    plan_id int,
    plan_name varchar(64),
    pid varchar(32),
    foreign key (uid) references UserInfo(uid),
    primary key (pid)
);

SHOW TABLES;
CREATE table Purchases (
	uid varchar(37),
    dt datetime,
    location varchar(64),
    amount decimal(6, 2),
    new_balance decimal(7, 2),
    plan_id int,
    pid varchar(32),
    foreign key (uid) references UserInfo(uid),
    primary key (pid)
);

SHOW TABLES;
CREATE table SessionData (
	uid varchar(37),
    theme varchar(16) DEFAULT 'dark',
    skey varchar(32),
    default_plan int,
    primary key (uid),
    foreign key (uid) references UserInfo(uid)
);

SHOW TABLES;