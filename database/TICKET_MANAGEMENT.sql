-- ====================================
-- IT HELPDESK TICKET MANAGEMENT
-- ====================================
-- Tuần 1 | Thiết kế bảng, dữ liệu mẫu và thực hành vòng đời ticket bằng SQLite.
-- init_db.py đọc tới dòng PART 2. Migration sau Tuần 4 nằm trong migrations.py.

-- Bật kiểm tra khóa ngoại cho kết nối đang chạy script.
PRAGMA foreign_keys = ON;

-- Bảng USERS | UNIQUE giữ email riêng biệt, CHECK giới hạn ba vai trò.

CREATE TABLE USERS
(
    USER_ID INTEGER PRIMARY KEY,
    FULL_NAME TEXT NOT NULL,
    EMAIL TEXT NOT NULL UNIQUE,
    ROLE TEXT NOT NULL
        CHECK (ROLE IN ('employee', 'technician', 'admin'))
);

-- Bảng CATEGORIES | Ticket lưu ID danh mục. Đổi tên danh mục ở một bảng.

CREATE TABLE CATEGORIES
(
    CATEGORY_ID INTEGER PRIMARY KEY,
    CATEGORY_NAME TEXT NOT NULL UNIQUE,
    DESCRIPTION TEXT
);

-- Bảng TICKETS | Ticket mới mặc định open. ASSIGNED_TO có thể NULL khi chưa giao.

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


-- Lịch sử giữ người thực hiện, trạng thái trước/sau và ghi chú để truy vết.
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
-- Đọc lại bảng để kiểm tra dữ liệu mẫu trước khi thực hành cập nhật.
-- =====================================

SELECT * FROM USERS;

SELECT * FROM CATEGORIES;

SELECT * FROM TICKETS;

SELECT * FROM TICKET_HISTORY;

-- =====================================
-- PART 4: ASSIGN TICKET #1
-- Chỉ giao ticket open cho technician. changes() ngăn ghi lịch sử nếu UPDATE không đổi dòng nào.
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
-- Dùng điều kiện theo người được giao và trạng thái hiện tại, rồi xác minh cả ticket và lịch sử.
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
-- Employee xác nhận ticket resolved của mình. Code Python bổ sung nhánh mở lại ở Tuần 2.
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
