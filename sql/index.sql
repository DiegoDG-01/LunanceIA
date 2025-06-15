-- Additional Indexes for Performance Improvement
CREATE INDEX idx_transactions_user_type_date ON transactions(user_id, type, transaction_date);
CREATE INDEX idx_accounts_user_active ON accounts(user_id, is_active);
CREATE INDEX idx_budgets_date ON budgets(start_date, end_date);