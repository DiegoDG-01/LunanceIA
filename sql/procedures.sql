-- Stored Procedure to Generate Subscription Charges
DELIMITER //
CREATE PROCEDURE generate_subscription_charges()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE v_subscription_id INT;
    DECLARE v_user_id INT;
    DECLARE v_account_id INT;
    DECLARE v_category_id INT;
    DECLARE v_amount DECIMAL(12,2);
    DECLARE v_frequency VARCHAR(20);
    DECLARE v_last_charge_date DATE;
    DECLARE v_next_charge_date DATE;

    DECLARE cur CURSOR FOR
        SELECT s.subscription_id, s.user_id, s.account_id, s.category_id,
               s.amount, s.frequency
        FROM subscriptions s
        WHERE s.is_active = TRUE
        AND (s.end_date IS NULL OR s.end_date >= CURDATE());

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    OPEN cur;

    read_loop: LOOP
        FETCH cur INTO v_subscription_id, v_user_id, v_account_id,
                      v_category_id, v_amount, v_frequency;

        IF done THEN
            LEAVE read_loop;
        END IF;

        -- Get the last charge date
        SELECT MAX(charge_date) INTO v_last_charge_date
        FROM subscription_charges
        WHERE subscription_id = v_subscription_id
        AND status = 'paid';

        -- Calculate next date based on frequency
        CASE v_frequency
            WHEN 'daily' THEN
                SET v_next_charge_date = DATE_ADD(IFNULL(v_last_charge_date, CURDATE()), INTERVAL 1 DAY);
            WHEN 'weekly' THEN
                SET v_next_charge_date = DATE_ADD(IFNULL(v_last_charge_date, CURDATE()), INTERVAL 1 WEEK);
            WHEN 'biweekly' THEN
                SET v_next_charge_date = DATE_ADD(IFNULL(v_last_charge_date, CURDATE()), INTERVAL 2 WEEK);
            WHEN 'monthly' THEN
                SET v_next_charge_date = DATE_ADD(IFNULL(v_last_charge_date, CURDATE()), INTERVAL 1 MONTH);
            WHEN 'quarterly' THEN
                SET v_next_charge_date = DATE_ADD(IFNULL(v_last_charge_date, CURDATE()), INTERVAL 3 MONTH);
            WHEN 'semiannual' THEN
                SET v_next_charge_date = DATE_ADD(IFNULL(v_last_charge_date, CURDATE()), INTERVAL 6 MONTH);
            WHEN 'annual' THEN
                SET v_next_charge_date = DATE_ADD(IFNULL(v_last_charge_date, CURDATE()), INTERVAL 1 YEAR);
        END CASE;

        -- Generate pending charges if the date has passed
        WHILE v_next_charge_date <= CURDATE() DO
            INSERT INTO subscription_charges (subscription_id, charge_date, amount, status)
            VALUES (v_subscription_id, v_next_charge_date, v_amount, 'pending');

            -- Calculate next date
            CASE v_frequency
                WHEN 'daily' THEN
                    SET v_next_charge_date = DATE_ADD(v_next_charge_date, INTERVAL 1 DAY);
                WHEN 'weekly' THEN
                    SET v_next_charge_date = DATE_ADD(v_next_charge_date, INTERVAL 1 WEEK);
                WHEN 'biweekly' THEN
                    SET v_next_charge_date = DATE_ADD(v_next_charge_date, INTERVAL 2 WEEK);
                WHEN 'monthly' THEN
                    SET v_next_charge_date = DATE_ADD(v_next_charge_date, INTERVAL 1 MONTH);
                WHEN 'quarterly' THEN
                    SET v_next_charge_date = DATE_ADD(v_next_charge_date, INTERVAL 3 MONTH);
                WHEN 'semiannual' THEN
                    SET v_next_charge_date = DATE_ADD(v_next_charge_date, INTERVAL 6 MONTH);
                WHEN 'annual' THEN
                    SET v_next_charge_date = DATE_ADD(v_next_charge_date, INTERVAL 1 YEAR);
            END CASE;
        END WHILE;
    END LOOP;

    CLOSE cur;
END//
DELIMITER ;