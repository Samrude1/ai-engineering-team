# Architecture Blueprint: Trading Simulation Platform

## 1. Overview
The Trading Simulation Platform provides an enterprise simulation environment for managing cash balances, executing equity transactions (AAPL, TSLA, GOOGL), tracking holdings, calculating portfolio profit/loss against deposits, and enforcing risk controls (no overdrafts, no short selling).

## 2. Core Class & Architecture

### `Account` (in `accounts.py`)

#### State & Attributes:
- `user_id: str`: Unique identifier for the account.
- `balance: float`: Current available cash balance.
- `holdings: dict[str, int]`: Mapping of stock ticker symbols to quantity of owned shares.
- `transactions: list[dict]`: Chronological audit log of all financial and trading transactions.
- `initial_deposit_total: float`: Cumulative cash deposited into the account for ROI calculations.
- `next_id: int`: Monotonically increasing counter for unique transaction ID assignment.

#### Method Signatures:
- `deposit(amount: float) -> bool`: Adds funds to cash balance.
- `withdraw(amount: float) -> bool`: Withdraws cash provided `balance >= amount`.
- `buy_shares(symbol: str, quantity: int, price: float) -> bool`: Purchases shares if cash balance covers total cost (`price * quantity`).
- `sell_shares(symbol: str, quantity: int, price: float) -> bool`: Sells shares if currently held quantity covers order.
- `get_portfolio_value(prices: dict[str, float]) -> float`: Calculates total net worth (`cash + sum(holdings * price)`).
- `get_profit_loss(prices: dict[str, float]) -> float`: Calculates net P&L (`portfolio_value - total_deposits`).
- `get_holdings() -> dict[str, int]`: Returns a copy of current active stock positions.
- `get_transactions() -> list[dict]`: Returns copy of immutable transaction history.

## 3. Security & Invariant Guarantees
1. No negative balances allowed on withdrawals or purchases.
2. Short selling is prevented (cannot sell shares exceeding holdings).
3. Monotonic ID assignment guarantees distinct transaction audit trails.
