import unittest
from accounts import Account

class TestAccount(unittest.TestCase):
    def setUp(self):
        self.account = Account("test_trader")

    def test_deposit_and_balance(self):
        self.assertTrue(self.account.deposit(5000.0))
        self.assertEqual(self.account.balance, 5000.0)
        self.assertEqual(self.account.total_deposits, 5000.0)

    def test_invalid_deposit(self):
        self.assertFalse(self.account.deposit(-100.0))
        self.assertFalse(self.account.deposit(0))
        self.assertEqual(self.account.balance, 0.0)

    def test_withdrawal(self):
        self.account.deposit(1000.0)
        self.assertTrue(self.account.withdraw(400.0))
        self.assertEqual(self.account.balance, 600.0)

    def test_overdraw_protection(self):
        self.account.deposit(500.0)
        self.assertFalse(self.account.withdraw(600.0))
        self.assertEqual(self.account.balance, 500.0)

    def test_buy_shares(self):
        self.account.deposit(1000.0)
        # AAPL mock price is 182.50. 2 * 182.50 = 365.00
        self.assertTrue(self.account.buy_shares("AAPL", 2))
        self.assertEqual(self.account.holdings["AAPL"], 2)
        self.assertEqual(self.account.balance, 1000.0 - 365.0)

    def test_buy_exceeding_balance(self):
        self.account.deposit(100.0)
        self.assertFalse(self.account.buy_shares("AAPL", 5))
        self.assertEqual(self.account.balance, 100.0)

    def test_sell_shares(self):
        self.account.deposit(1000.0)
        self.account.buy_shares("AAPL", 2)
        self.assertTrue(self.account.sell_shares("AAPL", 1))
        self.assertEqual(self.account.holdings["AAPL"], 1)

    def test_sell_unowned_shares(self):
        self.account.deposit(1000.0)
        self.assertFalse(self.account.sell_shares("TSLA", 1))

    def test_portfolio_value_and_pnl(self):
        self.account.deposit(1000.0)
        self.account.buy_shares("AAPL", 2, price=100.0)
        # balance = 800, holdings = 2 AAPL
        # With new price of 150: portfolio value = 800 + 300 = 1100, P&L = +100
        val = self.account.get_portfolio_value({"AAPL": 150.0})
        self.assertEqual(val, 1100.0)
        pnl = self.account.get_profit_loss({"AAPL": 150.0})
        self.assertEqual(pnl, 100.0)

if __name__ == "__main__":
    unittest.main()
