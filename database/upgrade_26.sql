-- Run once after upgrade_25.sql. Test-only statuses; no payment provider.
ALTER TABLE payout_reservations DROP CONSTRAINT IF EXISTS payout_reservations_status_check;
ALTER TABLE payout_reservations ADD CONSTRAINT payout_reservations_status_check
  CHECK(status IN ('reserved_test','cancelled_test'));
