# SQL SELECT Project

This repository demonstrates the use of SQL `SELECT` statements to query databases effectively. The project is based on tasks and concepts learned in a project-based course and was implemented using DataSpell, Docker, DBeaver, and PostgreSQL on a local machine. Below are the details and structure of the repository.

## Project Overview

This project aims to provide a hands-on approach to retrieving and manipulating data from tables in a PostgreSQL database using SQL `SELECT` statements.

### Objectives
- Retrieve data from tables of a database using SQL `SELECT` statements.
- Use SQL operators with the `WHERE` clause to set conditions on tables for data manipulation.
- Utilize wildcard characters and other comparison operators for flexible data retrieval.
- Sort and limit query results while using SQL aliases for temporary naming.

### Tools Used
- **DataSpell**: For integrated database query management.
- **Docker**: For containerizing the PostgreSQL database.
- **DBeaver**: For visual database interaction.
- **PostgreSQL**: As the database management system.

### Course Structure Tasks Implemented

#### Task 1: SELECT - FROM
- Retrieve all data from the `employees`, `departments`, and `salaries` tables.

#### Task 2: SELECT - FROM AND WHERE
- Retrieve specific data from a table using the `WHERE` clause with conditions.

#### Task 3: SQL Operators
- Use `AND` and `OR` operators with the `WHERE` clause.
- Understand operator precedence.
- Utilize `IN` and `NOT IN` operators.

#### Task 4: Wildcard Characters
- Retrieve data using `LIKE` and `NOT LIKE` operators with `%` and `_` wildcard characters.

#### Task 5: SQL Operators - Part 2
- Use `BETWEEN` and `IS NULL` / `IS NOT NULL` operators with the `WHERE` clause.

#### Task 6: Other Comparison Operators
- Use equality (`=`), inequality (`<>`, `!=`), greater than (`>`), less than (`<`), and their combinations.

#### Task 7: SELECT DISTINCT, ORDER BY, LIMIT, and SQL Aliases
- Retrieve distinct data from tables.
- Sort query results using `ORDER BY`.
- Limit the result set with `LIMIT`.
- Assign temporary names to columns using SQL aliases.

### Files Included

- **SQL Files for Practice:**
  - `querying_databases.sql`: Contains all the SQL queries used in the project.
  - `employee_excerpt.sql`: Sample data to simulate the `employees` database.

### Instructions for Setup

1. Install PostgreSQL on your local machine.
2. Load the provided `.sql` files into your PostgreSQL instance:
   - Use `psql` or DBeaver to execute the SQL files.
   - Ensure the database is correctly set up with the provided schema and data.
3. Use any SQL client (e.g., DBeaver) to query the database using the examples provided in the SQL files.

### Example Queries

#### Retrieve All Data
```sql
SELECT * FROM employees;
```

#### Retrieve Specific Columns
```sql
SELECT first_name, last_name, hire_date FROM employees;
```

#### Using WHERE Clause
```sql
SELECT * FROM employees WHERE hire_date > '2000-01-01';
```

#### Using SQL Operators
```sql
SELECT * FROM employees WHERE dept_no = 'd003' AND hire_date <= '1999-12-31';
```

#### Using Wildcard Characters
```sql
SELECT * FROM employees WHERE first_name LIKE 'A%';
```

### Earn a Certificate

After completing the tasks and quizzes outlined in this project, you can assess your understanding by attempting graded and ungraded quizzes. Ensure you score higher than 80% to earn a certificate of completion. I have successfully completed this course and earned the certificate.

### Meet the Instructor
Olayinka Imisioluwa Arimoro is a Data Scientist passionate about solving healthcare challenges with machine learning and deep learning techniques. His goal is to teach relevant skills for deriving business insights.

### Next Steps
- Use the provided `.sql` files for practice.
- Experiment with modifying the queries to explore the database further.
- Document your learning journey and insights in the repository.

## License
This repository is open for educational purposes. Feel free to use, modify, and share with proper attribution.

---

Happy querying! 🚀
