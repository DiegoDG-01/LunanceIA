-- Useful Views

-- Monthly Summary View by User
CREATE VIEW monthly_summary AS
SELECT
    u.user_id,
    u.name AS user_name,
    YEAR(t.transaction_date) AS year,
    MONTH(t.transaction_date) AS month,
    SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END) AS total_income,
    SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END) AS total_expenses,
    SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE -t.amount END) AS balance
FROM users u
LEFT JOIN transactions t ON u.user_id = t.user_id
GROUP BY u.user_id, YEAR(t.transaction_date), MONTH(t.transaction_date);

-- Expenses by Category View
CREATE VIEW expenses_by_category AS
SELECT
    u.user_id,
    c.name AS category_name,
    YEAR(t.transaction_date) AS year,
    MONTH(t.transaction_date) AS month,
    SUM(t.amount) AS total_spent,
    COUNT(*) AS num_transactions
FROM transactions t
JOIN users u ON t.user_id = u.user_id
JOIN categories c ON t.category_id = c.category_id
WHERE t.type = 'expense'
GROUP BY u.user_id, c.category_id, YEAR(t.transaction_date), MONTH(t.transaction_date);

-- Active Subscriptions with Estimated Monthly Cost View
CREATE VIEW active_subscriptions_monthly_cost AS
SELECT
    s.user_id,
    s.name,
    s.amount,
    s.frequency,
    CASE
        WHEN s.frequency = 'monthly' THEN s.amount
        WHEN s.frequency = 'annual' THEN s.amount / 12
        WHEN s.frequency = 'quarterly' THEN s.amount / 3
        WHEN s.frequency = 'semiannual' THEN s.amount / 6
        WHEN s.frequency = 'biweekly' THEN s.amount * 2
        WHEN s.frequency = 'weekly' THEN s.amount * 4.33
        WHEN s.frequency = 'daily' THEN s.amount * 30
    END AS estimated_monthly_cost
FROM subscriptions s
WHERE s.is_active = TRUE AND (s.end_date IS NULL OR s.end_date > CURDATE());
