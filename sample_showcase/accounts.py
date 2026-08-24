"""
Module providing account management and trading simulation functionalities.
"""
from typing import Dict, List, Any

# Mock market price feed for simulation testing
MOCK_MARKET_PRICES = {
    "AAPL": 182.50,
    "TSLA": 215.30,
    "GOOGL": 140.20,
    "NVDA": 480.00
}

def get_share_price(symbol: str) -> float:
    """Returns mock real-time share price for supported symbols."""
    return MOCK_MARKET_PRICES.get(symbol.upper(), 100.0)


class Account:
    """
    Class representing a user account in the trading simulation platform.
    Provides methods for managing funds, recording transactions, and tracking portfolio metrics.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.balance: float = 0.0
        self.total_deposits: float = 0.0
        self.holdings: Dict[str, int] = {}
        self.transactions: List[Dict[str, Any]] = []
        self.next_id: int = 1

    def deposit(self, amount: float) -> bool:
        """Deposit funds into account balance."""
        if not isinstance(amount, (int, float)) or amount <= 0:
            return False

        self.balance += float(amount)
        self.total_deposits += float(amount)
        self._record_tx("deposit", {"amount": float(amount), "balance_after": self.balance})
        return True

    def withdraw(self, amount: float) -> bool:
        """Withdraw funds from available balance."""
        if not isinstance(amount, (int, float)) or amount <= 0 or amount > self.balance:
            return False

        self.balance -= float(amount)
        self._record_tx("withdraw", {"amount": float(amount), "balance_after": self.balance})
        return True

    def buy_shares(self, symbol: str, quantity: int, price: float = None) -> bool:
        """Buy shares of a given symbol."""
        if not symbol or not isinstance(quantity, int) or quantity <= 0:
            return False

        sym = symbol.upper()
        exec_price = float(price) if price is not None else get_share_price(sym)
        total_cost = exec_price * quantity

        if total_cost > self.balance:
            return False

        self.balance -= total_cost
        self.holdings[sym] = self.holdings.get(sym, 0) + quantity
        self._record_tx("buy", {
            "symbol": sym,
            "quantity": quantity,
            "price": exec_price,
            "total": total_cost,
            "balance_after": self.balance
        })
        return True

    def sell_shares(self, symbol: str, quantity: int, price: float = None) -> bool:
        """Sell shares of a given symbol."""
        if not symbol or not isinstance(quantity, int) or quantity <= 0:
            return False

        sym = symbol.upper()
        current_holding = self.holdings.get(sym, 0)
        if quantity > current_holding:
            return False

        exec_price = float(price) if price is not None else get_share_price(sym)
        total_revenue = exec_price * quantity

        self.balance += total_revenue
        self.holdings[sym] -= quantity
        if self.holdings[sym] == 0:
            del self.holdings[sym]

        self._record_tx("sell", {
            "symbol": sym,
            "quantity": quantity,
            "price": exec_price,
            "total": total_revenue,
            "balance_after": self.balance
        })
        return True

    def get_portfolio_value(self, price_feed: Dict[str, float] = None) -> float:
        """Calculate current total portfolio value (cash + equity)."""
        holdings_value = 0.0
        feed = price_feed or MOCK_MARKET_PRICES
        for sym, qty in self.holdings.items():
            price = feed.get(sym, get_share_price(sym))
            holdings_value += price * qty
        return round(self.balance + holdings_value, 2)

    def get_profit_loss(self, price_feed: Dict[str, float] = None) -> float:
        """Calculate overall profit/loss relative to total deposits."""
        current_val = self.get_portfolio_value(price_feed)
        return round(current_val - self.total_deposits, 2)

    def get_holdings(self) -> Dict[str, int]:
        """Return current share holdings."""
        return dict(self.holdings)

    def get_transactions(self) -> List[Dict[str, Any]]:
        """Return transaction log."""
        return list(self.transactions)

    def _record_tx(self, action: str, details: Dict[str, Any]):
        tx = {
            "tx_id": self.next_id,
            "action": action,
            **details
        }
        self.transactions.append(tx)
        self.next_id += 1
