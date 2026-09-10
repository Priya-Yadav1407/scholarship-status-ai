USE scholarship_db;

CREATE TABLE students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    course VARCHAR(100),
    marks INT,
    family_income DECIMAL(12,2),
    scholarship_amount DECIMAL(12,2),
    scholarship_status VARCHAR(50)
);

INSERT INTO students
(name, course, marks, family_income, scholarship_amount, scholarship_status)
VALUES
('Rahul Sharma', 'Computer Science', 85, 150000, 10000, 'Approved'),
('Priya Singh', 'Engineering', 92, 120000, 15000, 'Approved'),
('Amit Kumar', 'Commerce', 70, 300000, 5000, 'Pending'),
('Sneha Patel', 'Computer Science', 95, 100000, 20000, 'Approved'),
('Ravi Verma', 'Engineering', 65, 400000, 0, 'Rejected');

SELECT * FROM students;

USE scholarship_db;

CREATE TABLE scholarships (
    scholarship_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    scholarship_name VARCHAR(100),
    provider VARCHAR(100),
    scholarship_amount DECIMAL(12,2),

    FOREIGN KEY (student_id)
    REFERENCES students(student_id)
);

INSERT INTO scholarships
(student_id, scholarship_name, provider, scholarship_amount)
VALUES
(1, 'Merit Scholarship', 'Government', 10000),
(2, 'Engineering Excellence Scholarship', 'University', 15000),
(3, 'Commerce Support Scholarship', 'Government', 5000),
(4, 'Academic Excellence Scholarship', 'University', 20000);

SELECT * FROM scholarships;

SELECT
    students.name,
    students.course,
    scholarships.scholarship_name,
    scholarships.provider,
    scholarships.scholarship_amount
FROM students
INNER JOIN scholarships
ON students.student_id = scholarships.student_id;

SELECT
    students.name,
    students.course,
    scholarships.scholarship_name,
    scholarships.provider,
    scholarships.scholarship_amount
FROM students
LEFT JOIN scholarships
ON students.student_id = scholarships.student_id;