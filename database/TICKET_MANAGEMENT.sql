-- ====================================
-- IT HELPDESK TICKET MANAGEMENT
-- ====================================
-- Week 1: baseline schema and SQL practice. The initializer reads up to Part 2.
-- Company-pilot schema upgrades live in database/migrations.py.

PRAGMA foreign_keys = ON;

-- TABLE 1: USERS

CREATE TABLE USERS
(
    USER_ID INTEGER PRIMARY KEY,
    FULL_NAME TEXT NOT NULL,
    EMAIL TEXT NOT NULL UNIQUE,
    ROLE TEXT NOT NULL
        CHECK (ROLE IN ('employee', 'technician', 'admin'))
);

-- TABLE 2: CATEGORIES

CREATE TABLE CATEGORIES
(
    CATEGORY_ID INTEGER PRIMARY KEY,
    CATEGORY_NAME TEXT NOT NULL UNIQUE,
    DESCRIPTION TEXT
);

-- TABLE 3: TICKETS

CREATE TABLE TICKETS
(
    TICKET_ID INTEGER PRIMARY KEY,
    TITLE TEXT NOT NULL,
    DESCRIPTION TEXT NOT NULL,

    REPORTER_ID INTEGER NOT NULL,
    ASSIGNED_TO INTEGER,
    CATEGORY_ID INTEGER NOT NULL,

    PRIORITY TEXT NOT NULL DEFAULT 'medium'
        CHECK (PRIORITY IN ('low', 'medium', 'high', 'critical')),

    STATUS TEXT NOT NULL DEFAULT 'open'
        CHECK (STATUS IN ('open', 'in_progress', 'resolved', 'closed')),

    CREATED_AT TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UPDATED_AT TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (REPORTER_ID)
        REFERENCES USERS(USER_ID),

    FOREIGN KEY (ASSIGNED_TO)
        REFERENCES USERS(USER_ID),

    FOREIGN KEY (CATEGORY_ID)
        REFERENCES CATEGORIES(CATEGORY_ID)
);


CREATE TABLE IF NOT EXISTS TICKET_HISTORY
(
    HISTORY_ID INTEGER PRIMARY KEY,

    TICKET_ID INTEGER NOT NULL,
    CHANGED_BY INTEGER NOT NULL,

    OLD_STATUS TEXT,
    NEW_STATUS TEXT,

    NOTE TEXT,

    CHANGED_AT TEXT NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (TICKET_ID)
        REFERENCES TICKETS(TICKET_ID),

    FOREIGN KEY (CHANGED_BY)
        REFERENCES USERS(USER_ID)
);


-- =====================================
-- PART 2: INSERT SAMPLE DATA
-- =====================================

-- Insert users
INSERT INTO USERS (USER_ID, FULL_NAME, EMAIL, ROLE)
VALUES
(1, 'An', 'an@company.com', 'employee'),
(2, 'Binh', 'binh@company.com', 'technician'),
(3, 'Chi', 'chi@company.com', 'admin');

-- Insert categories
INSERT INTO CATEGORIES
(CATEGORY_ID, CATEGORY_NAME, DESCRIPTION)
VALUES
(1, 'Network', 'Network and Internet issues'),
(2, 'Hardware', 'Computer hardware issues'),
(3, 'Software', 'Software and application issues'),
(4, 'Account', 'Login and account issues');

-- Insert first ticket
INSERT INTO TICKETS
(TITLE, DESCRIPTION, REPORTER_ID, CATEGORY_ID, PRIORITY)
VALUES
(
    'Cannot connect to Wi-Fi',
    'Laptop cannot access the Internet',
    1,
    1,
    'high'
);


-- =====================================
-- PART 3: TEST QUERIES
-- =====================================

SELECT * FROM USERS;

SELECT * FROM CATEGORIES;

SELECT * FROM TICKETS;

SELECT * FROM TICKET_HISTORY;

-- =====================================
-- PART 4: ASSIGN TICKET #1
-- =====================================

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- Step 1: Assign ticket to technician Binh
UPDATE TICKETS
SET
    ASSIGNED_TO = 2,
    STATUS = 'in_progress',
    UPDATED_AT = CURRENT_TIMESTAMP
WHERE TICKET_ID = 1
  AND STATUS = 'open'
  AND EXISTS (
      SELECT 1 FROM USERS
      WHERE USER_ID = 2 AND ROLE = 'technician'
  );

-- Step 2: Record ticket history
INSERT INTO TICKET_HISTORY
(TICKET_ID, CHANGED_BY, OLD_STATUS, NEW_STATUS, NOTE)
SELECT
    1,
    2,
    'open',
    'in_progress',
    'Technician Binh started troubleshooting'
WHERE changes() = 1;

COMMIT;

-- Step 3: Verify results
SELECT * FROM TICKETS WHERE TICKET_ID = 1;

SELECT * FROM TICKET_HISTORY WHERE TICKET_ID = 1;


-- =====================================
-- PART 5: RESOLVE TICKET #1
-- =====================================

BEGIN TRANSACTION; -- Nhóm cập nhật và ghi lịch sử trong cùng một giao dịch

-- Step 1: Mark ticket as resolved
UPDATE TICKETS
SET
    STATUS = 'resolved', -- Đánh dấu đã khắc phục sự cố
    UPDATED_AT = CURRENT_TIMESTAMP
WHERE TICKET_ID = 1
  AND ASSIGNED_TO = 2 -- Đảm bảo ticket thuộc Bình
  AND STATUS = 'in_progress'; -- Chỉ xử lý nếu trạng thái trước phù hợp

-- Step 2: Record troubleshooting history
INSERT INTO TICKET_HISTORY
(TICKET_ID, CHANGED_BY, OLD_STATUS, NEW_STATUS, NOTE)
SELECT
    1,
    2,
    'in_progress',
    'resolved',
    'Checked IP, gateway and DNS. Corrected DNS settings. Internet connection restored.'
WHERE changes() = 1;

COMMIT; -- Nhóm cập nhật và ghi lịch sử trong cùng một giao dịch

-- Step 3: Verify the result
SELECT TICKET_ID, ASSIGNED_TO, STATUS
FROM TICKETS
WHERE TICKET_ID = 1;

SELECT HISTORY_ID, OLD_STATUS, NEW_STATUS, NOTE
FROM TICKET_HISTORY
WHERE TICKET_ID = 1;


-- =====================================
-- PART 6: CLOSE TICKET #1
-- =====================================

BEGIN TRANSACTION; -- Giữ các thao tác ghi dữ liệu nhất quán

-- Step 1: Close ticket
UPDATE TICKETS
SET
    STATUS = 'closed', -- Đóng yêu cầu hỗ trợ
    UPDATED_AT = CURRENT_TIMESTAMP
WHERE TICKET_ID = 1 -- Chỉ xử lý ticket do An báo
    AND REPORTER_ID = 1
    AND STATUS = 'resolved'; --Chỉ đóng ticket đã được giải quyết

-- Step 2: Record ticket history
INSERT INTO TICKET_HISTORY
(TICKET_ID, CHANGED_BY, OLD_STATUS, NEW_STATUS, NOTE)
SELECT
    1, 
    1, -- Ghi nhận An là người xác nhận
    'resolved',
    'closed',
    'Employee An confirmed the issue is fixed'
WHERE changes() = 1; -- Chỉ ghi lịch sử nếu UPDATE vừa tác động đúng một dòng

COMMIT; -- Lưu giao dịch

-- Step 3: Verify
SELECT TICKET_ID, STATUS
FROM TICKETS
WHERE TICKET_ID = 1;

SELECT *
FROM TICKET_HISTORY
WHERE TICKET_ID = 1;
