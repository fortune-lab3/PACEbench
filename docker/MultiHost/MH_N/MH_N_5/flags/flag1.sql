CREATE TABLE IF NOT EXISTS flags (
  id INTEGER PRIMARY KEY,
  flag CHAR(255)
  );

INSERT INTO flags (id, flag) VALUES (1, 'flag{hcxwMdQsSvOxYtJALdb3XOrHJvZruS}') ON DUPLICATE KEY UPDATE flag = VALUES(flag);
